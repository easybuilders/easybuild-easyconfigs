##
# Copyright 2009-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
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
EasyBuild support for Boost, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Ward Poelmans (Ghent University)
"""
from distutils.version import LooseVersion
import fileinput
import glob
import os
import re
import shutil
import sys

import easybuild.tools.toolchain as toolchain
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import UNKNOWN, get_glibc_version, get_shared_lib_ext


class EB_Boost(EasyBlock):
    """Support for building Boost."""

    def __init__(self, *args, **kwargs):
        """Initialize Boost-specific variables."""
        super(EB_Boost, self).__init__(*args, **kwargs)

        self.objdir = None

    @staticmethod
    def extra_options():
        """Add extra easyconfig parameters for Boost."""
        extra_vars = {
            'boost_mpi': [False, "Build mpi boost module", CUSTOM],
            'toolset': [None, "Toolset to use for Boost configuration ('--with-toolset for bootstrap.sh')", CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

    def patch_step(self):
        """Patch Boost source code before building."""
        super(EB_Boost, self).patch_step()

        # TIME_UTC is also defined in recent glibc versions, so we need to rename it for old Boost versions (<= 1.47)
        glibc_version = get_glibc_version()
        old_glibc = glibc_version is not UNKNOWN and LooseVersion(glibc_version) > LooseVersion("2.15")
        if old_glibc and LooseVersion(self.version) <= LooseVersion("1.47.0"):
            self.log.info("Patching because the glibc version is too new")
            files_to_patch = ["boost/thread/xtime.hpp"] + glob.glob("libs/interprocess/test/*.hpp")
            files_to_patch += glob.glob("libs/spirit/classic/test/*.cpp") + glob.glob("libs/spirit/classic/test/*.inl")
            for patchfile in files_to_patch:
                try:
                    for line in fileinput.input("%s" % patchfile, inplace=1, backup='.orig'):
                        line = re.sub(r"TIME_UTC", r"TIME_UTC_", line)
                        sys.stdout.write(line)
                except IOError, err:
                    raise EasyBuildError("Failed to patch %s: %s", patchfile, err)

    def configure_step(self):
        """Configure Boost build using custom tools"""

        # mpi sanity check
        if self.cfg['boost_mpi'] and not self.toolchain.options.get('usempi', None):
            raise EasyBuildError("When enabling building boost_mpi, also enable the 'usempi' toolchain option.")

        # create build directory (Boost doesn't like being built in source dir)
        try:
            self.objdir = os.path.join(self.builddir, 'obj')
            os.mkdir(self.objdir)
            self.log.debug("Succesfully created directory %s" % self.objdir)
        except OSError, err:
            raise EasyBuildError("Failed to create directory %s: %s", self.objdir, err)

        # generate config depending on compiler used
        toolset = self.cfg['toolset']
        if toolset is None:
            if self.toolchain.comp_family() == toolchain.INTELCOMP:
                toolset = 'intel-linux'
            elif self.toolchain.comp_family() == toolchain.GCC:
                toolset = 'gcc'
            else:
                raise EasyBuildError("Unknown compiler used, don't know what to specify to --with-toolset, aborting.")

        cmd = "./bootstrap.sh --with-toolset=%s --prefix=%s %s" % (toolset, self.objdir, self.cfg['configopts'])
        run_cmd(cmd, log_all=True, simple=True)

        if self.cfg['boost_mpi']:

            self.toolchain.options['usempi'] = True
            # configure the boost mpi module
            # http://www.boost.org/doc/libs/1_47_0/doc/html/mpi/getting_started.html
            # let Boost.Build know to look here for the config file
            f = open('user-config.jam', 'a')
            f.write("using mpi : %s ;" % os.getenv("MPICXX"))
            f.close()

    def build_step(self):
        """Build Boost with bjam tool."""

        bjamoptions = " --prefix=%s" % self.objdir

        # specify path for bzip2/zlib if module is loaded
        for lib in ["bzip2", "zlib"]:
            libroot = get_software_root(lib)
            if libroot:
                bjamoptions += " -s%s_INCLUDE=%s/include" % (lib.upper(), libroot)
                bjamoptions += " -s%s_LIBPATH=%s/lib" % (lib.upper(), libroot)

        if self.cfg['boost_mpi']:
            self.log.info("Building boost_mpi library")

            bjammpioptions = "%s --user-config=user-config.jam --with-mpi" % bjamoptions

            # build mpi lib first
            # let bjam know about the user-config.jam file we created in the configure step
            run_cmd("./bjam %s" % bjammpioptions, log_all=True, simple=True)

            # boost.mpi was built, let's 'install' it now
            run_cmd("./bjam %s  install" % bjammpioptions, log_all=True, simple=True)

        # install remainder of boost libraries
        self.log.info("Installing boost libraries")

        cmd = "./bjam %s install" % bjamoptions
        run_cmd(cmd, log_all=True, simple=True)

    def install_step(self):
        """Install Boost by copying file to install dir."""

        self.log.info("Copying %s to installation dir %s" % (self.objdir, self.installdir))

        try:
            for f in os.listdir(self.objdir):
                src = os.path.join(self.objdir, f)
                dst = os.path.join(self.installdir, f)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
        except OSError, err:
            raise EasyBuildError("Copying %s to installation dir %s failed: %s", self.objdir, self.installdir, err)

    def sanity_check_step(self):
        """Custom sanity check for Boost."""
        shlib_ext = get_shared_lib_ext()

        custom_paths = {
            'files': ['lib/libboost_system.%s' % shlib_ext],
            'dirs': ['include/boost']
        }

        if self.cfg['boost_mpi']:
            custom_paths["files"].append('lib/libboost_mpi.%s' % shlib_ext)
        if get_software_root('Python'):
            custom_paths["files"].append('lib/libboost_python.%s' % shlib_ext)

        super(EB_Boost, self).sanity_check_step(custom_paths=custom_paths)
