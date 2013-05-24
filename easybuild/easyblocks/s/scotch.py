##
# Copyright 2009-2013 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
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
EasyBuild support for SCOTCH, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import fileinput
import os
import re
import sys
import shutil
from distutils.version import LooseVersion

import easybuild.tools.toolchain as toolchain
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import run_cmd, copytree


class EB_SCOTCH(EasyBlock):
    """Support for building/installing SCOTCH."""

    def configure_step(self):
        """Configure SCOTCH build: locate the template makefile, copy it to a general Makefile.inc and patch it."""

        # pick template makefile
        comp_fam = self.toolchain.comp_family()
        if comp_fam == toolchain.INTELCOMP:  #@UndefinedVariable
            makefilename = 'Makefile.inc.x86-64_pc_linux2.icc'
        elif comp_fam == toolchain.GCC:  #@UndefinedVariable
            makefilename = 'Makefile.inc.x86-64_pc_linux2'
        else:
            self.log.error("Unknown compiler family used: %s" % comp_fam)

        # create Makefile.inc
        try:
            srcdir = os.path.join(self.cfg['start_dir'], 'src')
            src = os.path.join(srcdir, 'Make.inc', makefilename)
            dst = os.path.join(srcdir, 'Makefile.inc')
            shutil.copy2(src, dst)
            self.log.debug("Successfully copied Makefile.inc to src dir.")
        except OSError:
            self.log.error("Copying Makefile.inc to src dir failed.")

        # the default behaviour of these makefiles is still wrong
        # e.g., compiler settings, and we need -lpthread
        try:
            for line in fileinput.input(dst, inplace=1, backup='.orig.easybuild'):
                # use $CC and the likes since we're at it.
                line = re.sub(r"^CCS\s*=.*$", "CCS\t= $(CC)", line)
                line = re.sub(r"^CCP\s*=.*$", "CCP\t= $(MPICC)", line)
                line = re.sub(r"^CCD\s*=.*$", "CCD\t= $(MPICC)", line)
                # append -lpthread to LDFLAGS
                line = re.sub(r"^LDFLAGS\s*=(?P<ldflags>.*$)", "LDFLAGS\t=\g<ldflags> -lpthread", line)
                sys.stdout.write(line)
        except IOError, err:
            self.log.error("Can't modify/write Makefile in 'Makefile.inc': %s" % (err))

        # change to src dir for building
        try:
            os.chdir(srcdir)
            self.log.debug("Changing to src dir.")
        except OSError, err:
            self.log.error("Failed to change to src dir: %s" % err)

    def build_step(self):
        """Build by running build_step, but with some special options for SCOTCH depending on the compiler."""

        ccs = os.environ['CC']
        ccp = os.environ['MPICC']
        ccd = os.environ['MPICC']

        cflags = "-fPIC -O3 -DCOMMON_FILE_COMPRESS_GZ -DCOMMON_PTHREAD -DCOMMON_RANDOM_FIXED_SEED -DSCOTCH_RENAME"
        if self.toolchain.comp_family() == toolchain.GCC:  #@UndefinedVariable
            cflags += " -Drestrict=__restrict"
        else:
            cflags += " -restrict -DIDXSIZE64"

        if not self.toolchain.mpi_family() in [toolchain.INTELMPI, toolchain.QLOGICMPI]:  #@UndefinedVariable
            cflags += " -DSCOTCH_PTHREAD"

        # actually build
        apps = ['scotch', 'ptscotch']
        if LooseVersion(self.version) >= LooseVersion('6.0'):
            # separate target for esmumps in recent versions
            apps.extend(['esmumps', 'ptesmumps'])
        for app in apps:
            cmd = 'make CCS="%s" CCP="%s" CCD="%s" CFLAGS="%s" %s' % (ccs, ccp, ccd, cflags, app)
            run_cmd(cmd, log_all=True, simple=True)

    def install_step(self):
        """Install by copying files and creating group library file."""

        self.log.debug("Installing SCOTCH")

        # copy files to install dir
        regmetis = re.compile(r".*metis.*")
        try:
            for d in ["include", "lib", "bin", "man"]:
                src = os.path.join(self.cfg['start_dir'], d)
                dst = os.path.join(self.installdir, d)
                # we don't need any metis stuff from scotch!
                copytree(src, dst, ignore=lambda path, files: [x for x in files if regmetis.match(x)])

        except OSError, err:
            self.log.error("Copying %s to installation dir %s failed: %s" % (src, dst, err))

        # create group library file
        scotchlibdir = os.path.join(self.installdir, 'lib')
        scotchgrouplib = os.path.join(scotchlibdir, 'libscotch_group.a')

        try:
            line = ' '.join(os.listdir(scotchlibdir))
            line = "GROUP (%s)" % line

            f = open(scotchgrouplib, 'w')
            f.write(line)
            f.close()
            self.log.info("Successfully written group lib file: %s" % scotchgrouplib)
        except (IOError, OSError), err:
            self.log.error("Can't write to file %s: %s" % (scotchgrouplib, err))

    def sanity_check_step(self):
        """Custom sanity check for SCOTCH."""

        custom_paths = {
                        'files': ['bin/%s' % x for x in ["acpl", "amk_fft2", "amk_hy", "amk_p2", "dggath",
                                                         "dgord", "dgscat", "gbase", "gmap", "gmk_m2",
                                                         "gmk_msh", "gmtst", "gotst", "gpart", "gtst",
                                                         "mmk_m2", "mord", "amk_ccc", "amk_grf", "amk_m2",
                                                         "atst", "dgmap", "dgpart", "dgtst", "gcv", "gmk_hy",
                                                         "gmk_m3", "gmk_ub2", "gord", "gout", "gscat", "mcv",
                                                         "mmk_m3", "mtst"]] +
                                 ['include/%s.h' % x for x in ["esmumps","ptscotchf", "ptscotch","scotchf",
                                                               "scotch"]] +
                                 ['lib/lib%s.a' % x for x in ["esmumps","ptscotch", "ptscotcherrexit",
                                                              "scotcherr", "scotch_group", "ptesmumps",
                                                              "ptscotcherr", "scotch", "scotcherrexit"]],
                        'dirs':[]
                        }

        super(EB_SCOTCH, self).sanity_check_step(custom_paths=custom_paths)
