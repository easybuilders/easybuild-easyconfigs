##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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
EasyBuild support for building and installing LAPACK, implemented as an easyblock
"""

import glob
import os
import shutil

from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd


# also used for e.g. ScaLAPACK
def get_blas_lib(log):
    """
    Determine BLAS lib to provide to e.g. LAPACK for building/testing
    """
    blaslib = None
    known_blas_libs = {
                       'GotoBLAS': '-L%s -lgoto',
                       'ATLAS': '-L%s -lf77blas -latlas'
                      }
    for (key,val) in known_blas_libs.items():
        softroot = 'SOFTROOT%s' % key.upper()
        if os.getenv(softroot):
            blaslib = val % os.path.join(os.getenv(softroot), 'lib')
            log.debug("Found %s, so using %s as BLAS lib" % (softroot, key))
            break
        else:
            log.debug("%s not defined, so %s not loaded" % (softroot, key))

    if not blaslib:
        log.error("No or unknown BLAS lib loaded; known BLAS libs: %s" % known_blas_libs.keys())

    return blaslib


class LAPACK(Application):
    """
    Support for building LAPACK
    - read make.inc.example and replace BLAS line with configtops
    -- should be replaced by patch and variables.
    """

    def __init__(self, *args, **kwargs):
        Application.__init__(self, *args, **kwargs)

    def extra_options(self):
        extra_vars = {
                      'supply_blas': [False, "Supply BLAS lib to LAPACK for building (default: False)"],
                      'test_only': [False, "Only make tests, don't try and build LAPACK lib."]
                     }
        return Application.extra_options(self, extra_vars)


    def configure(self):
        """
        Configure LAPACK for build: copy make.inc and set make options
        """

        # copy make.inc file from examples
        if os.getenv('SOFTROOTGCC'):
            makeinc = 'gfortran'
        elif os.getenv('SOFTROOTIFORT'):
            makeinc = 'ifort'
        else:
            self.log.error("Don't know which make.inc file to pick, unknown compiler being used...")

        src = os.path.join(self.getcfg('startfrom'), 'INSTALL', 'make.inc.%s' % makeinc)
        dest = os.path.join(self.getcfg('startfrom'), 'make.inc')

        if not os.path.isfile(src):
            self.log.error("Can't find source file %s" % src)

        if os.path.exists(dest):
            self.log.error("Destination file %s exists" % dest)

        try:
            shutil.copy(src, dest)
        except OSError, err:
            self.log.error("Copying %s to %s failed: %s" % (src, dest, err))

        # set optimization flags
        fpic = ''
        if self.toolkit().opts['pic']:
            fpic = '-fPIC'
        self.updatecfg('makeopts', 'OPTS="$FFLAGS -m64" NOOPT="%s -m64 -O0"' % fpic)

        # prematurely exit configure when we're only testing
        if self.getcfg('test_only'):
            self.log.info('Only testing, so skipping rest of configure.')
            return

        # supply blas lib (or not)
        if self.getcfg('supply_blas'):

            blaslib = get_blas_lib(self.log)

            self.log.debug("Providing '%s' as BLAS lib" % blaslib)
            self.updatecfg('makeopts', 'BLASLIB="%s"' % blaslib)

        else:
            self.log.debug("Not providing a BLAS lib to LAPACK.")
            self.updatecfg('makeopts', 'BLASLIB=""')

        # only build library if we're not supplying a BLAS library (otherwise testing fails)
        if not self.getcfg('supply_blas'):
            self.log.info('No BLAS library provided, so only building LAPACK library (no testing).')
            self.updatecfg('makeopts', 'lib')

    # don't create a module if we're only testing
    def make(self):
        """
        Only build when we're not testing.
        """
        if self.getcfg('test_only'):
            return

        else:
            # default make suffices (for now)
            Application.make(self)

    def make_install(self):
        """
        Install LAPACK: copy all .a files to lib dir in install directory
        """

        if self.getcfg('test_only'):
            self.log.info('Only testing, so skipping make install.')
            pass

        srcdir = self.getcfg('startfrom')
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
            self.log.error("Copying %s to installation dir %s failed: %s" % (srcdir, destdir, err))

    def test(self):
        """
        Run BLAS and LAPACK tests that come with netlib's LAPACK.
        """
        if self.getcfg('test_only'):

            if not os.getenv('SOFTROOTLAPACK'):
                self.log.error("You need to make sure that the LAPACK module is loaded to perform testing.")

            blaslib = get_blas_lib(self.log)

            self.log.info('Running BLAS and LAPACK tests included.')

            # run BLAS and LAPACK tests
            for lib in ["blas", "lapack"]:
                self.log.info("Running %s tests..." % lib.upper())
                cmd = "make BLASLIB='%s' %s_testing" % (blaslib, lib)
                run_cmd(cmd, log_all=True, simple=True)
        else:
            Application.test(self)

    # don't create a module if we're only testing
    def make_module(self, fake=False):
        """
        Only make LAPACK module when we're not testing.
        """
        if self.getcfg('test_only'):
            pass
        else:
            return Application.make_module(self, fake)

    def sanitycheck(self):
        """
        Custom sanity check for LAPACK (only run when not testing)
        """
        if not self.getcfg('test_only'):
            if not self.getcfg('sanityCheckPaths'):
                self.setcfg('sanityCheckPaths',{
                                                'files': ["lib/%s" % x for x in ["liblapack.a", "libtmglib.a"]],
                                                'dirs': []
                                               })

                self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

            Application.sanitycheck(self)
