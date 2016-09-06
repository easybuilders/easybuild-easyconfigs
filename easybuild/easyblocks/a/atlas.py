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
EasyBuild support for building and installing ATLAS, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import fileinput
import re
import os
import sys
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_cpu_speed, get_shared_lib_ext


class EB_ATLAS(ConfigureMake):
    """
    Support for building ATLAS
    - configure (and check if it failed due to CPU throttling being enabled)
    - avoid parallel build (doesn't make sense for ATLAS and doesn't work)
    - make (optionally with shared libs), and install
    """

    def __init__(self, *args, **kwargs):
        super(EB_ATLAS, self).__init__(*args, **kwargs)

    @staticmethod
    def extra_options():
        extra_vars = {
            'ignorethrottling': [False, "Ignore check done by ATLAS for CPU throttling (not recommended)", CUSTOM],
            'full_lapack': [False, "Build a full LAPACK library (requires netlib's LAPACK)", CUSTOM],
            'sharedlibs': [False, "Enable building of shared libs as well", CUSTOM],
        }
        return ConfigureMake.extra_options(extra_vars)

    def configure_step(self):

        # configure for 64-bit build
        self.cfg.update('configopts', "-b 64")

        if self.cfg['ignorethrottling']:
            # ignore CPU throttling check
            # this is not recommended, it will disturb the measurements done by ATLAS
            # used for the EasyBuild demo, to avoid requiring root privileges
            if LooseVersion(self.version) < LooseVersion('3.10.0'):
                self.cfg.update('configopts', '-Si cputhrchk 0')
            else:
                self.log.warning("Ignore CPU throttling check is not possible via command line.")
                # apply patch to ignore CPU throttling: make ProbeCPUThrottle always return 0
                # see http://sourceforge.net/p/math-atlas/support-requests/857/
                cfg_file = os.path.join('CONFIG', 'src', 'config.c')
                for line in fileinput.input(cfg_file, inplace=1, backup='.orig.eb'):
                    line = re.sub(r"^(\s*iret)\s*=\s*.*CPU THROTTLE.*$", r"\1 = 0;", line)
                    sys.stdout.write(line)
            self.log.warning('CPU throttling check ignored: NOT recommended!')

        # use cycle accurate timer for timings
        # see http://math-atlas.sourceforge.net/atlas_install/node23.html
        # this should work on Linux with both GCC and Intel compilers
        cpu_freq = int(get_cpu_speed())
        self.cfg.update('configopts', "-D c -DPentiumCPS=%s" % cpu_freq)


        # if LAPACK is found, instruct ATLAS to provide a full LAPACK library
        # ATLAS only provides a few LAPACK routines natively
        if self.cfg['full_lapack']:
            lapack_lib_version = LooseVersion('3.9')
            if LooseVersion(self.version) < lapack_lib_version:
                # pass built LAPACK library
                lapack = get_software_root('LAPACK')
                if lapack:
                    self.cfg.update('configopts', ' --with-netlib-lapack=%s/lib/liblapack.a' % lapack)
                else:
                    raise EasyBuildError("netlib's LAPACK library not available, required to build ATLAS "
                                         "with a full LAPACK library.")
            else:
                # pass LAPACK source tarball
                lapack_src = None
                for src in self.src:
                    if src['name'].startswith('lapack'):
                        lapack_src = src['path']
                if lapack_src is not None:
                    self.cfg.update('configopts', ' --with-netlib-lapack-tarfile=%s' % lapack_src)
                else:
                    raise EasyBuildError("LAPACK source tarball not available, but required.")

        # enable building of shared libraries (requires -fPIC)
        if self.cfg['sharedlibs'] or self.toolchain.options['pic']:
            self.log.debug("Enabling -fPIC because we're building shared ATLAS libs, or just because.")
            self.cfg.update('configopts', '-Fa alg -fPIC')

        # ATLAS only wants to be configured/built in a separate dir'
        try:
            objdir = "obj"
            os.makedirs(objdir)
            os.chdir(objdir)
        except OSError, err:
            raise EasyBuildError("Failed to create obj directory to build in: %s", err)

        # specify compilers
        self.cfg.update('configopts', '-C ic %(cc)s -C if %(f77)s' % {
                                                                     'cc':os.getenv('CC'),
                                                                     'f77':os.getenv('F77')
                                                                    })

        # call configure in parent dir
        cmd = "%s %s/configure --prefix=%s %s" % (self.cfg['preconfigopts'], self.cfg['start_dir'],
                                                 self.installdir, self.cfg['configopts'])
        (out, exitcode) = run_cmd(cmd, log_all=False, log_ok=False, simple=False)

        if exitcode != 0:
            throttling_regexp = re.compile("cpu throttling [a-zA-Z]* enabled", re.IGNORECASE)
            if throttling_regexp.search(out):
                errormsg = ' '.join([
                    "Configure failed, possible because CPU throttling is enabled; ATLAS doesn't like that. ",
                    "You can either disable CPU throttling, or set 'ignorethrottling' to True in the ATLAS .eb spec file.",
                    "Also see http://math-atlas.sourceforge.net/errata.html#cputhrottle .",
                    "Configure output: %s",
                ]) % out
            else:
                errormsg = "configure output: %s\nConfigure failed, not sure why (see output above)." % out
            raise EasyBuildError(errormsg)

    def build_step(self, verbose=False):

        if self.cfg['parallel'] != 1:
            self.log.warning("Ignoring requested build parallelism, it breaks ATLAS, so setting to 1")
            self.cfg['parallel'] = 1

        # default make is fine
        super(EB_ATLAS, self).build_step(verbose=verbose)

        # optionally also build shared libs
        if self.cfg['sharedlibs']:
            try:
                os.chdir('lib')
            except OSError, err:
                raise EasyBuildError("Failed to change to 'lib' directory for building the shared libs.", err)

            self.log.debug("Building shared libraries")
            cmd = "make shared cshared ptshared cptshared"
            run_cmd(cmd, log_all=True, simple=True)

            try:
                os.chdir('..')
            except OSError, err:
                raise EasyBuildError("Failed to get back to previous dir after building shared libs: %s ", err)

    def install_step(self):
        """Install step

        Default make install and optionally remove incomplete lapack libs.
        If the full_lapack option was set to false we don't
        """
        super(EB_ATLAS, self).install_step()
        if not self.cfg['full_lapack']:
            for i in ['liblapack.a', 'liblapack.%s' % get_shared_lib_ext()]:
                lib = os.path.join(self.installdir, "lib", i[0])
                if os.path.exists(lib):
                    os.rename(lib, os.path.join(self.installdir, "lib",
                                                lib.replace("liblapack", "liblapack_atlas")))
                else:
                    self.log.warning("Tried to remove %s, but file didn't exist")


    def test_step(self):

        # always run tests
        if self.cfg['runtest']:
            self.log.warning("ATLAS testing is done using 'make check' and 'make ptcheck',"\
                             " so no need to set 'runtest' in the .eb spec file.")

        # sanity tests
        self.cfg['runtest'] = 'check'
        super(EB_ATLAS, self).test_step()

        # checks of threaded code (only if required)
        if os.path.exists(os.path.join(self.cfg['start_dir'], 'obj', 'include', 'atlas_pthreads.h')):
            self.cfg['runtest'] = 'ptcheck'
            super(EB_ATLAS, self).test_step()

        # performance summary
        self.cfg['runtest'] = 'time'
        super(EB_ATLAS, self).test_step()

    # default make install is fine

    def sanity_check_step(self):
        """
        Custom sanity check for ATLAS
        """

        libs = ["atlas", "cblas", "f77blas", "lapack", "ptcblas", "ptf77blas"]

        static_libs = ["lib/lib%s.a" % x for x in libs]

        if self.cfg['sharedlibs']:
            shlib_ext = get_shared_lib_ext()
            shared_libs = ["lib/lib%s.%s" % (x, shlib_ext) for x in libs]
        else:
            shared_libs = []

        custom_paths = {
                        'files': ["include/%s" % x for x in ["cblas.h", "clapack.h"]] +
                                 static_libs + shared_libs,
                        'dirs': ["include/atlas"]
                       }

        super(EB_ATLAS, self).sanity_check_step(custom_paths=custom_paths)
