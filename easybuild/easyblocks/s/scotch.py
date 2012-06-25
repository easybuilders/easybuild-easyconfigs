##
# Copyright 2009-2012 Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
#
# http://github.com/hpcugent/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""
This module contains the SCOTCH easyblock.
"""
import fileinput
import os
import re
import sys
import shutil
from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd, copytree


class SCOTCH(Application):
    """
    Easyblock for building SCOTCH
    """
    def configure(self):
        """
        Locate the correct makefile, and copy this to a general Makefile.inc
        (as shipped and expected by SCOTCH)
        """
        if "SOFTROOTICC" in os.environ:
            makefilename = 'Makefile.inc.x86-64_pc_linux2.icc'

        elif "SOFTROOTGCC" in os.environ:
            makefilename = 'Makefile.inc.x86-64_pc_linux2'
        else:
            self.log.error("Don't know how to handle toolkit %s." % self.tk.name)

        try:
            srcdir = os.path.join(self.getcfg('startfrom'), 'src')
            src = os.path.join(srcdir, 'Make.inc', makefilename)
            dst = os.path.join(srcdir, 'Makefile.inc')
            shutil.copy2(src, dst)
            self.log.debug("Successfully copied Makefile.inc to src dir.")
        except OSError:
            self.log.error("Copying Makefile.inc to src dir failed.")

        #the default behaviour of these makefiles is still wrong
        #e.g., we need -lpthread  
        try:
            for line in fileinput.input(dst, inplace=1, backup='.orig.patchictce'):
                #use $CC and the like since we're at it.
                line = re.sub(r"^CCS\s*=.*$", "CCS\t= $(CC)", line)
                line = re.sub(r"^CCP\s*=.*$", "CCP\t= $(MPICC)", line)
                line = re.sub(r"^CCD\s*=.*$", "CCD\t= $(MPICC)", line)
                #append -lpthread to LDFLAGS
                line = re.sub(r"^LDFLAGS\s*=(?P<ldflags>.*$)", "LDFLAGS\t=\g<ldflags> -lpthread", line)
                sys.stdout.write(line)
        except IOError, err:
            self.log.error("Can't modify/write Makefile in 'Makefile.inc': %s" % (err))

        try:
            os.chdir(srcdir)
            self.log.debug("Changing to src dir.")
        except OSError, err:
            self.log.error("Failed to change to src dir: %s" % err)

    def make(self):
        """
        Run make, but with some special options for SCOTCH depending on the compiler
        """
        ccs = os.environ['CC']
        ccp = os.environ['MPICC']
        ccd = os.environ['MPICC']
        cflags = ""
        #if self.tk.name == "iqacml":
        #    cflags = "-fPIC -O3 -DCOMMON_FILE_COMPRESS_GZ -DCOMMON_PTHREAD -DCOMMON_RANDOM_FIXED_SEED -DSCOTCH_RENAME -restrict -DIDXSIZE64"
        #GCC doens't know -restrict
        if not "SOFTROOTGCC" in os.environ:
            cflags = "-fPIC -O3 -DCOMMON_FILE_COMPRESS_GZ -DCOMMON_PTHREAD -DCOMMON_RANDOM_FIXED_SEED -DSCOTCH_RENAME -DSCOTCH_PTHREAD -restrict -DIDXSIZE64"
        else:
            cflags = "-fPIC -O3 -DCOMMON_FILE_COMPRESS_GZ -DCOMMON_PTHREAD -DCOMMON_RANDOM_FIXED_SEED -DSCOTCH_RENAME -DSCOTCH_PTHREAD -Drestrict=__restrict"
        cmd = 'make CCS="%s" CCP="%s" CCD="%s" CFLAGS="%s" scotch' % (ccs, ccp, ccd, cflags)
        run_cmd(cmd, log_all=True, simple=True)
        cmd = 'make CCS="%s" CCP="%s" CCD="%s" CFLAGS="%s" ptscotch' % (ccs, ccp, ccd, cflags)
        run_cmd(cmd, log_all=True, simple=True)

    def make_install(self):
        self.log.debug("starting scotch's make_install")
        regmetis = re.compile(r".*metis.*")
        try:
            for d in ["include", "lib", "bin", "man"]:#removed , here, we don't need metis.h etc.
                src = os.path.join(self.getcfg('startfrom'), d)
                dst = os.path.join(self.installdir, d)
                #we don't need any metis stuff from scotch!
                copytree(src, dst, ignore=lambda path, files: [x for x in files if regmetis.match(x)])

        except OSError, err:
            self.log.error("Copying %s to installation dir %s failed: %s" % (src, dst, err))

        scotchlibdir = os.path.join(self.installdir, 'lib')
        scotchgrouplib = os.path.join(scotchlibdir, 'libscotch_group.a')

        liblistorig = os.listdir(scotchlibdir)
        line = ' '.join(liblistorig)
        line = "GROUP (%s)" % line
        try:
            f = open(scotchgrouplib, 'w')
            f.write(line)
            f.close()
            self.log.info("Successfully written group lib file: %s" % scotchgrouplib)
        except IOError, err:
            self.log.error("Can't write to file %s: %s" % (scotchgrouplib, err))
