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
EasyBuild support for building and installing LAPACK, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import glob
import os
import shutil

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.toolchains.linalg.atlas import Atlas
from easybuild.toolchains.linalg.gotoblas import GotoBLAS
from easybuild.toolchains.linalg.openblas import OpenBLAS
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd

# also used for e.g. ScaLAPACK
def get_blas_lib(log):
    """
    Determine BLAS lib to provide to e.g. LAPACK for building/testing
    """
    log.deprecated("get_blas_lib uses hardcoded list of known BLAS libs, should rely on toolchain support", '3.0')
    blaslib = None
    known_blas_libs = {
                       'GotoBLAS': GotoBLAS.BLAS_LIB,
                       'ATLAS': Atlas.BLAS_LIB,
                       'OpenBLAS': OpenBLAS.BLAS_LIB,
                      }
    for (key, libs) in known_blas_libs.items():
        root = get_software_root(key)
        if root:
            blaslib = "-L%s %s" % (os.path.join(root, 'lib'), ' '.join(['-l%s' % lib for lib in libs]))
            log.debug("Using %s as BLAS lib" % root)
            break
        else:
            log.debug("%s module not loaded" % key)

    if not blaslib:
        raise EasyBuildError("No or unknown BLAS lib loaded; known BLAS libs: %s", known_blas_libs.keys())

    return blaslib


class EB_LAPACK(ConfigureMake):
    """
    Support for building LAPACK
    - read build_step.inc.example and replace BLAS line with configtops
    -- should be replaced by patch and variables.
    """

    @staticmethod
    def extra_options():
        extra_vars = {
            'supply_blas': [False, "Supply BLAS lib to LAPACK for building", CUSTOM],
            'test_only': [False, "Only make tests, don't try and build LAPACK lib", CUSTOM],
        }
        return ConfigureMake.extra_options(extra_vars)

    def configure_step(self):
        """
        Configure LAPACK for build: copy build_step.inc and set make options
        """

        # copy build_step.inc file from examples
        if self.toolchain.comp_family() == toolchain.GCC:  #@UndefinedVariable
            makeinc = 'gfortran'
        elif self.toolchain.comp_family() == toolchain.INTELCOMP:  #@UndefinedVariable
            makeinc = 'ifort'
        else:
            raise EasyBuildError("Don't know which build_step.inc file to pick, unknown compiler being used...")

        src = os.path.join(self.cfg['start_dir'], 'INSTALL', 'make.inc.%s' % makeinc)
        dest = os.path.join(self.cfg['start_dir'], 'make.inc')

        if not os.path.isfile(src):
            raise EasyBuildError("Can't find source file %s", src)

        if os.path.exists(dest):
            raise EasyBuildError("Destination file %s exists", dest)

        try:
            shutil.copy(src, dest)
        except OSError, err:
            raise EasyBuildError("Copying %s to %s failed: %s", src, dest, err)

        # set optimization flags
        fpic = ''
        if self.toolchain.options['pic']:
            fpic = '-fPIC'
        self.cfg.update('buildopts', 'OPTS="$FFLAGS -m64" NOOPT="%s -m64 -O0"' % fpic)

        # prematurely exit configure when we're only testing
        if self.cfg['test_only']:
            self.log.info('Only testing, so skipping rest of configure.')
            return

        # supply blas lib (or not)
        if self.cfg['supply_blas']:

            blaslib = get_blas_lib(self.log)

            self.log.debug("Providing '%s' as BLAS lib" % blaslib)
            self.cfg.update('buildopts', 'BLASLIB="%s"' % blaslib)

        else:
            self.log.debug("Not providing a BLAS lib to LAPACK.")
            self.cfg.update('buildopts', 'BLASLIB=""')

        # only build library if we're not supplying a BLAS library (otherwise testing fails)
        if not self.cfg['supply_blas']:
            self.log.info('No BLAS library provided, so only building LAPACK library (no testing).')
            self.cfg.update('buildopts', 'lib')

    # don't create a module if we're only testing
    def build_step(self):
        """
        Only build when we're not testing.
        """
        if self.cfg['test_only']:
            return

        else:
            # default make suffices (for now)
            super(EB_LAPACK, self).build_step()

    def install_step(self):
        """
        Install LAPACK: copy all .a files to lib dir in install directory
        """

        if self.cfg['test_only']:
            self.log.info('Only testing, so skipping make install.')
            pass

        srcdir = self.cfg['start_dir']
        destdir = os.path.join(self.installdir, 'lib')

        try:
            os.makedirs(destdir)

            # copy all .a files
            os.chdir(srcdir)
            for lib in glob.glob('*.a'):
                srcfile = os.path.join(srcdir, lib)
                self.log.debug("Copying file %s to dir %s" % (srcfile, destdir))
                shutil.copy2(srcfile, destdir)

            # symlink libraries to sensible names, if they aren't renamed already
            for (fromfile, tofile) in [('liblapack_LINUX.a', 'liblapack.a'),
                                       ('tmglib_LINUX.a', 'libtmglib.a')]:
                frompath = os.path.join(destdir, fromfile)
                topath = os.path.join(destdir, tofile)
                if os.path.isfile(frompath) and not os.path.isfile(tofile):
                    self.log.debug("Symlinking %s to %s" % (fromfile, tofile))
                    os.symlink(frompath, topath)

        except OSError, err:
            raise EasyBuildError("Copying %s to installation dir %s failed: %s", srcdir, destdir, err)

    def load_module(self, mod_paths=None, purge=True):
        """Don't try to load (non-existing) LAPACK module when performing a test build."""
        if not self.cfg['test_only']:
            super(EB_LAPACK, self).load_module(mod_paths=mod_paths, purge=purge)

    def test_step(self):
        """
        Run BLAS and LAPACK tests that come with netlib's LAPACK.
        """
        if self.cfg['test_only']:

            if not get_software_root('LAPACK'):
                raise EasyBuildError("You need to make sure that the LAPACK module is loaded to perform testing.")

            blaslib = get_blas_lib(self.log)

            self.log.info('Running BLAS and LAPACK tests included.')

            # run BLAS and LAPACK tests
            for lib in ["blas", "lapack"]:
                self.log.info("Running %s tests..." % lib.upper())
                cmd = "make BLASLIB='%s' %s_testing" % (blaslib, lib)
                run_cmd(cmd, log_all=True, simple=True)
        else:
            super(EB_LAPACK, self).test_step()

    # don't create a module if we're only testing
    def make_module_step(self, fake=False):
        """
        Only make LAPACK module when we're not testing.
        """
        if self.cfg['test_only']:
            pass
        else:
            return super(EB_LAPACK, self).make_module_step(fake)

    def sanity_check_step(self):
        """
        Custom sanity check for LAPACK (only run when not testing)
        """
        if not self.cfg['test_only']:
            custom_paths = {
                            'files': ["lib/%s" % x for x in ["liblapack.a", "libtmglib.a"]],
                            'dirs': []
                           }

            super(EB_LAPACK, self).sanity_check_step(custom_paths=custom_paths)
