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
EasyBuild support for building and installing ATLAS, implemented as an easyblock
"""

import re
import os

from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd
from easybuild.tools.modules import get_software_root


class ATLAS(Application):
    """
    Support for building ATLAS
    - configure (and check if it failed due to CPU throttling being enabled)
    - avoid parallel build (doesn't make sense for ATLAS and doesn't work)
    - make (optionally with shared libs), and install
    """

    def __init__(self, *args, **kwargs):
        Application.__init__(self, *args, **kwargs)

    def extra_options(self):
        extra_vars = {
                      'ignorethrottling': [False, "Ignore check done by ATLAS for CPU throttling (not recommended) (default: False)"],
                      'full_lapack': [False, "Build a full LAPACK library (requires netlib's LAPACK) (default: False)"],
                      'sharedlibs': [False, "Enable building of shared libs as well (default: False)"]
                     }
        return Application.extra_options(self, extra_vars)

    def configure(self):

        # configure for 64-bit build
        self.updatecfg('configopts', "-b 64")

        if self.getcfg('ignorethrottling'):
            # ignore CPU throttling check
            # this is not recommended, it will disturb the measurements done by ATLAS
            # used for the EasyBuild demo, to avoid requiring root privileges
            self.updatecfg('configopts', '-Si cputhrchk 0')

        # if LAPACK is found, instruct ATLAS to provide a full LAPACK library
        # ATLAS only provides a few LAPACK routines natively
        if self.getcfg('full_lapack'):
            lapack = get_software_root('LAPACK')
            if lapack:
                self.updatecfg('configopts', ' --with-netlib-lapack=%s/lib/liblapack.a' % lapack)
            else:
                self.log.error("netlib's LAPACK library not available,"\
                               " required to build ATLAS with a full LAPACK library.")

        # enable building of shared libraries (requires -fPIC)
        if self.getcfg('sharedlibs') or self.toolkit().opts['pic']:
            self.log.debug("Enabling -fPIC because we're building shared ATLAS libs, or just because.")
            self.updatecfg('configopts', '-Fa alg -fPIC')

        # ATLAS only wants to be configured/built in a separate dir'
        try:
            objdir = "obj"
            os.makedirs(objdir)
            os.chdir(objdir)
        except OSError, err:
            self.log.error("Failed to create obj directory to build in: %s" % err)

        # specify compilers
        self.updatecfg('configopts', '-C ic %(cc)s -C if %(f77)s' % {
                                                                     'cc':os.getenv('CC'),
                                                                     'f77':os.getenv('F77')
                                                                    })

        # call configure in parent dir
        cmd = "%s %s/configure --prefix=%s %s" % (self.getcfg('preconfigopts'), self.getcfg('startfrom'),
                                                 self.installdir, self.getcfg('configopts'))
        (out, exitcode) = run_cmd(cmd, log_all=False, log_ok=False, simple=False)

        if exitcode != 0:
            throttling_regexp = re.compile("cpu throttling [a-zA-Z]* enabled", re.IGNORECASE)
            if throttling_regexp.search(out):
                errormsg = """Configure failed, possible because CPU throttling is enabled; ATLAS doesn't like that.
You can either disable CPU throttling, or set 'ignorethrottling' to True in the ATLAS .eb spec file.
Also see http://math-atlas.sourceforge.net/errata.html#cputhrottle .
Configure output:
%s """ % out
            else:
                errormsg = """configure output: %s
Configure failed, not sure why (see output above).""" % out
            self.log.error(errormsg)


    def setparallelism(self, nr=None):
        """
        Parallel build of ATLAS doesn't make sense (and doesn't work),
        because it collects timing etc., so disable it.
        """
        if not nr:
            self.log.warning("Ignoring requested parallelism, it breaks ATLAS, so setting to 1")
        self.log.info("Disabling parallel build, makes no sense for ATLAS.")
        Application.setparallelism(self, 1)


    def make(self, verbose=False):

        # default make is fine
        Application.make(self, verbose=verbose)

        # optionally also build shared libs
        if self.getcfg('sharedlibs'):
            try:
                os.chdir('lib')
            except OSError, err:
                self.log.error("Failed to change to 'lib' directory for building the shared libs." % err)

            self.log.debug("Building shared libraries")
            cmd = "make shared cshared ptshared cptshared"
            run_cmd(cmd, log_all=True, simple=True)

            try:
                os.chdir('..')
            except OSError, err:
                self.log.error("Failed to get back to previous dir after building shared libs: %s " % err)

    def make_install(self):
        """Install step

        Default make install and optionally remove incomplete lapack libs.
        If the full_lapack option was set to false we don't
        """
        Application.make_install(self)
        if not self.getcfg('full_lapack'):
            for i in ['liblapack.a', 'liblapack.so']:
                lib = os.path.join(self.installdir, "lib", i[0])
                if os.path.exists(lib):
                    os.rename(lib, os.path.join(self.installdir, "lib",
                                                lib.replace("liblapack", "liblapack_atlas")))
                else:
                    self.log.warning("Tried to remove %s, but file didn't exist")


    def test(self):

        # always run tests
        if self.getcfg('runtest'):
            self.log.warning("ATLAS testing is done using 'make check' and 'make ptcheck',"\
                             " so no need to set 'runtest' in the .eb spec file.")

        # sanity tests
        self.setcfg('runtest', 'check')
        Application.test(self)

        # checks of threaded code
        self.setcfg('runtest', 'ptcheck')
        Application.test(self)

        # performance summary
        self.setcfg('runtest', 'time')
        Application.test(self)

    # default make install is fine

    def sanitycheck(self):
        """
        Custom sanity check for ATLAS
        """
        if not self.getcfg('sanityCheckPaths'):

            libs = ["atlas", "cblas", "f77blas", "lapack", "ptcblas", "ptf77blas"]

            static_libs = ["lib/lib%s.a" % x for x in libs]

            if self.getcfg('sharedlibs'):
                shared_libs = ["lib/lib%s.so" % x for x in libs]
            else:
                shared_libs = []

            self.setcfg('sanityCheckPaths', {
                                             'files': ["include/%s" % x for x in ["cblas.h", "clapack.h"]] +
                                                    static_libs + shared_libs,
                                             'dirs': ["include/atlas"]
                                            })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
