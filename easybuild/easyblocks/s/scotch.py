##
# Copyright 2009-2012 Stijn Deweirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
import os
import re
import shutil
from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd

class SCOTCH(Application):
    """
    Easyblock for building SCOTCH
     """
    def configure(self):
        """
        Locate the correct makefile, and copy this to a general Makefile.inc
        (as shipped and expected by SCOTCH)
        """
        if self.tk.name in ['ictce', 'iqacml']:
            makefilename = 'Makefile.inc.x86-64_pc_linux2.icc'

        elif self.tk.name in ['goalf']:
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
        if self.tk.name == "iqacml":
            cflags = "-fPIC -O3 -DCOMMON_FILE_COMPRESS_GZ -DCOMMON_PTHREAD -DCOMMON_RANDOM_FIXED_SEED -DSCOTCH_RENAME -restrict -DIDXSIZE64"
        elif self.tk.name == 'ictce':
            cflags = "-fPIC -O3 -DCOMMON_FILE_COMPRESS_GZ -DCOMMON_PTHREAD -DCOMMON_RANDOM_FIXED_SEED -DSCOTCH_RENAME -DSCOTCH_PTHREAD -restrict -DIDXSIZE64"
        else:
            cflags = "-fPIC -O3 -DCOMMON_FILE_COMPRESS_GZ -DCOMMON_PTHREAD -DCOMMON_RANDOM_FIXED_SEED -DSCOTCH_RENAME -DSCOTCH_PTHREAD -Drestrict=__restrict"
        cmd = 'make CCS="%s" CCP="%s" CCD="%s" CFLAGS="%s" scotch' % (ccs, ccp, ccd, cflags)
        run_cmd(cmd, log_all=True, simple=True)
        cmd = 'make CCS="%s" CCP="%s" CCD="%s" CFLAGS="%s" ptscotch' % (ccs, ccp, ccd, cflags)
        run_cmd(cmd, log_all=True, simple=True)

    def make_install(self):
        try:
            for d in ["include", "lib", "bin", "man"]:
                src = os.path.join(self.getcfg('startfrom'), d)
                dst = os.path.join(self.installdir, d)
                shutil.copytree(src, dst)
        except OSError, err:
            self.log.error("Copying %s to installation dir %s failed: %s" % (src, dst, err))

        scotchlibdir = os.path.join(self.installdir, 'lib')
        scotchgrouplib = os.path.join(scotchlibdir, 'libscotch_group.a')
        liblistorig = os.listdir(scotchlibdir)
        liblist = []
        regmetis = re.compile(r".*metis.*")
        for lib in liblistorig:
            if not regmetis.match(lib): liblist.append(lib)
        line = ' '.join(liblist)
        line = "GROUP (%s)" % line
        try:
            f = open(scotchgrouplib, 'w')
            f.write(line)
            f.close()
            self.log.info("Successfully written group lib file: %s" % scotchgrouplib)
        except Exception, err:
            self.log.error("Can't write to file %s: %s" % (scotchgrouplib, err))
