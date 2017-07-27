##
# Copyright 2009-2017 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/easybuilders/easybuild
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
@author: Petar Forai (IMP/IMBA)
@author: Luca Marsella (CSCS)
@author: Guilherme Peretti-Pezzi (CSCS)
@author: Joachim Hein (Lund University)
@author: Michele Dolfi (ETH Zurich)
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
from easybuild.tools.filetools import write_file
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
            'boost_multi_thread': [False, "Build boost with multi-thread option", CUSTOM],
            'toolset': [None, "Toolset to use for Boost configuration ('--with-toolset for bootstrap.sh')", CUSTOM],
            'mpi_launcher': [None, "Launcher to use when running MPI regression tests", CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

    def patch_step(self):
        """Patch Boost source code before building."""
        super(EB_Boost, self).patch_step()

        # TIME_UTC is also defined in recent glibc versions, so we need to rename it for old Boost versions (<= 1.49)
        glibc_version = get_glibc_version()
        old_glibc = glibc_version is not UNKNOWN and LooseVersion(glibc_version) > LooseVersion("2.15")
        if old_glibc and LooseVersion(self.version) <= LooseVersion("1.49.0"):
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

        cmd = "%s ./bootstrap.sh --with-toolset=%s --prefix=%s %s"
        tup = (self.cfg['preconfigopts'], toolset, self.objdir, self.cfg['configopts'])
        run_cmd(cmd % tup, log_all=True, simple=True)

        if self.cfg['boost_mpi']:

            self.toolchain.options['usempi'] = True
            # configure the boost mpi module
            # http://www.boost.org/doc/libs/1_47_0/doc/html/mpi/getting_started.html
            # let Boost.Build know to look here for the config file

            txt = ''
            # Check if using a Cray toolchain and configure MPI accordingly
            if self.toolchain.toolchain_family() == toolchain.CRAYPE:
                if self.toolchain.PRGENV_MODULE_NAME_SUFFIX == 'gnu':
                    craympichdir = os.getenv('CRAY_MPICH2_DIR')
                    craygccversion = os.getenv('GCC_VERSION')
                    txt = '\n'.join([    
                        'local CRAY_MPICH2_DIR =  %s ;' % craympichdir,
                        'using gcc ',
                        ': %s' % craygccversion,
                        ': CC ',
                        ': <compileflags>-I$(CRAY_MPICH2_DIR)/include ',
                        '  <linkflags>-L$(CRAY_MPICH2_DIR)/lib \ ',
                        '; ',
                        'using mpi ',
                        ': CC ',
                        ': <find-shared-library>mpich ',
                        ': %s' % self.cfg['mpi_launcher'],
                        ';',
                        '',
                    ])
                else: 
                    raise EasyBuildError("Bailing out: only PrgEnv-gnu supported for now")
            else:
                txt = "using mpi : %s ;" % os.getenv("MPICXX")

            write_file('user-config.jam', txt, append=True)

    def build_boost_variant(self, bjamoptions, paracmd):
        """Build Boost library with specified options for bjam."""
        # build with specified options
        cmd = "%s ./bjam %s %s %s" % (self.cfg['prebuildopts'], bjamoptions, paracmd, self.cfg['buildopts'])
        run_cmd(cmd, log_all=True, simple=True)
        # install built Boost library
        cmd = "%s ./bjam %s install %s %s" % (self.cfg['preinstallopts'], bjamoptions, paracmd, self.cfg['installopts'])
        run_cmd(cmd, log_all=True, simple=True)
        # clean up before proceeding with next build    
        run_cmd("./bjam --clean-all", log_all=True, simple=True)

    def build_step(self):
        """Build Boost with bjam tool."""

        bjamoptions = " --prefix=%s" % self.objdir

        cxxflags = os.getenv('CXXFLAGS')
        if cxxflags is not None:
            bjamoptions += " cxxflags='%s'" % cxxflags 
        ldflags = os.getenv('LDFLAGS')
        if ldflags is not None:
            bjamoptions += " linkflags='%s'" % ldflags 

        # specify path for bzip2/zlib if module is loaded
        for lib in ["bzip2", "zlib"]:
            libroot = get_software_root(lib)
            if libroot:
                bjamoptions += " -s%s_INCLUDE=%s/include" % (lib.upper(), libroot)
                bjamoptions += " -s%s_LIBPATH=%s/lib" % (lib.upper(), libroot)

        paracmd = ''
        if self.cfg['parallel']:
            paracmd = "-j %s" % self.cfg['parallel']

        if self.cfg['boost_mpi']:
            self.log.info("Building boost_mpi library")
            self.build_boost_variant(bjamoptions + " --user-config=user-config.jam --with-mpi", paracmd)
        
        if self.cfg['boost_multi_thread']:
            self.log.info("Building boost with multi threading")
            self.build_boost_variant(bjamoptions + " threading=multi --layout=tagged", paracmd)

        # if both boost_mpi and boost_multi_thread are enabled, build boost mpi with multi-thread support
        if self.cfg['boost_multi_thread'] and self.cfg['boost_mpi']:
            self.log.info("Building boost_mpi with multi threading")
            extra_bjamoptions = " --user-config=user-config.jam --with-mpi threading=multi --layout=tagged"
            self.build_boost_variant(bjamoptions + extra_bjamoptions, paracmd)

        # install remainder of boost libraries
        self.log.info("Installing boost libraries")

        cmd = "%s ./bjam %s install %s %s" % (self.cfg['preinstallopts'], bjamoptions, paracmd, self.cfg['installopts'])
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
        if self.cfg['boost_multi_thread']:
            custom_paths["files"].append('lib/libboost_thread-mt.%s' % shlib_ext)
        if self.cfg['boost_mpi'] and self.cfg['boost_multi_thread']:
            custom_paths["files"].append('lib/libboost_mpi-mt.%s' % shlib_ext)

        super(EB_Boost, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Set up a BOOST_ROOT environment variable to e.g. ease Boost handling by cmake"""
        txt = super(EB_Boost, self).make_module_extra()
        txt += self.module_generator.set_environment('BOOST_ROOT', self.installdir)
        return txt
    
