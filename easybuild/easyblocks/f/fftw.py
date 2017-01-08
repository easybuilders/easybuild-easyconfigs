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
EasyBuild support for building and installing FFTW, implemented as an easyblock

@author: Kenneth Hoste (HPC-UGent)
"""
from vsc.utils.missing import nub

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.config import build_option
from easybuild.tools.systemtools import AARCH64, X86_64, get_cpu_architecture, get_cpu_features
from easybuild.tools.toolchain.compiler import OPTARCH_GENERIC


# AVX*, FMA, SSE2 (x86_64 only)
FFTW_CPU_FEATURE_FLAGS_SINGLE_DOUBLE = ['avx', 'avx2', 'avx512', 'fma', 'sse2', 'vsx']
# Altivec (POWER), SSE (x86), NEON (ARM), FMA (x86_64)
# asimd is CPU feature for extended NEON on AARCH64
FFTW_CPU_FEATURE_FLAGS = FFTW_CPU_FEATURE_FLAGS_SINGLE_DOUBLE + ['altivec', 'asimd', 'neon', 'sse']
FFTW_PRECISION_FLAGS = ['single', 'double', 'long-double', 'quad-precision']


class EB_FFTW(ConfigureMake):
    """Support for building/installing FFTW."""

    @staticmethod
    def _prec_param(prec):
        """Determine parameter name for specified precision"""
        return 'with_%s_prec' % prec.replace('-', '_').replace('_precision', '')

    @staticmethod
    def extra_options():
        """Custom easyconfig parameters for FFTW."""
        extra_vars = {
            'auto_detect_cpu_features': [True, "Auto-detect available CPU features, and configure accordingly", CUSTOM],
            'with_mpi': [True, "Enable building of FFTW MPI library", CUSTOM],
            'with_openmp': [True, "Enable building of FFTW OpenMP library", CUSTOM],
            'with_threads': [True, "Enable building of FFTW threads library", CUSTOM],
        }

        for flag in FFTW_CPU_FEATURE_FLAGS:
            help_msg = "Configure with --enable-%s (if None, auto-detect support for %s)" % (flag, flag.upper())
            extra_vars['use_%s' % flag] = [None, help_msg, CUSTOM]

        for prec in FFTW_PRECISION_FLAGS:
            help_msg = "Enable building of %s precision library" % prec.replace('-precision', '')
            extra_vars[EB_FFTW._prec_param(prec)] = [True, help_msg, CUSTOM]

        return ConfigureMake.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for FFTW."""
        super(EB_FFTW, self).__init__(*args, **kwargs)

        for flag in FFTW_CPU_FEATURE_FLAGS:
            # fail-safe: make sure we're not overwriting an existing attribute (could lead to weird bugs if we do)
            if hasattr(self, flag):
                raise EasyBuildError("EasyBlock attribute '%s' already exists")
            setattr(self, flag, self.cfg['use_%s' % flag])

        # auto-detect CPU features that can be used and are not enabled/disabled explicitly,
        # but only if --optarch=GENERIC is not being used
        if self.cfg['auto_detect_cpu_features']:

            # if --optarch=GENERIC is used, limit which CPU features we consider for auto-detection
            if build_option('optarch') == OPTARCH_GENERIC:
                cpu_arch = get_cpu_architecture()
                if cpu_arch == X86_64:
                    # SSE(2) is supported on all x86_64 architectures
                    cpu_features = ['sse', 'sse2']
                elif cpu_arch == AARCH64:
                    # NEON is supported on all AARCH64 architectures (indicated with 'asimd')
                    cpu_features = ['asimd']
                else:
                    cpu_features = []
            else:
                cpu_features = FFTW_CPU_FEATURE_FLAGS
            self.log.info("CPU features considered for auto-detection: %s", cpu_features)

            # get list of available CPU features, so we can check which ones to retain
            avail_cpu_features = get_cpu_features()

            # on macOS, AVX is indicated with 'avx1.0' rather than 'avx'
            if 'avx1.0' in avail_cpu_features:
                avail_cpu_features.append('avx')

            self.log.info("List of available CPU features: %s", avail_cpu_features)

            for flag in cpu_features:
                # only enable use of a particular CPU feature if it's still undecided (i.e. None)
                if getattr(self, flag) is None and flag in avail_cpu_features:
                    self.log.info("Enabling use of %s (should be supported based on CPU features)", flag.upper())
                    setattr(self, flag, True)

    def run_all_steps(self, *args, **kwargs):
        """
        Put configure options in place for different precisions (single, double, long double, quad).
        """
        # keep track of configopts specified in easyconfig file, so we can include them in each iteration later
        common_config_opts = self.cfg['configopts']

        self.cfg['configopts'] = []

        for prec in FFTW_PRECISION_FLAGS:
            if self.cfg[EB_FFTW._prec_param(prec)]:

                prec_configopts = []

                # double precison is the default, no configure flag needed (there is no '--enable-double')
                if prec != 'double':
                    prec_configopts.append('--enable-%s' % prec)

                # MPI is not supported for quad precision
                if prec != 'quad-precision' and self.cfg['with_mpi']:
                    prec_configopts.append('--enable-mpi')

                if self.toolchain.options['pic']:
                    prec_configopts.append('--with-pic')

                for libtype in ['openmp', 'threads']:
                    if self.cfg['with_%s' % libtype]:
                        prec_configopts.append('--enable-%s' % libtype)

                # SSE2, AVX* only supported for single/double precision
                if prec in ['single', 'double']:
                    for flag in FFTW_CPU_FEATURE_FLAGS_SINGLE_DOUBLE:
                        if getattr(self, flag):
                            if flag == 'fma':
                                prec_configopts.append('--enable-avx-128-fma')
                            else:
                                prec_configopts.append('--enable-%s' % flag)

                # Altivec (POWER) and SSE only for single precision
                for flag in ['altivec', 'sse']:
                    if prec == 'single' and getattr(self, flag):
                        prec_configopts.append('--enable-%s' % flag)

                # NEON (ARM) only for single precision and double precision (on AARCH64)
                if (prec == 'single' and (self.asimd or self.neon)) or (prec == 'double' and self.asimd):
                    prec_configopts.append('--enable-neon')

                # append additional configure options (may be empty string, but that's OK)
                self.cfg.update('configopts', [' '.join(prec_configopts) + common_config_opts])

        self.log.debug("List of configure options to iterate over: %s", self.cfg['configopts'])

        return super(EB_FFTW, self).run_all_steps(*args, **kwargs)

    def sanity_check_step(self):
        """Custom sanity check for FFTW."""

        custom_paths = {
            'files': ['bin/fftw-wisdom-to-conf', 'include/fftw3.f', 'include/fftw3.h'],
            'dirs': ['lib/pkgconfig'],
        }

        extra_files = []
        for (prec, letter) in [('double', ''), ('long_double', 'l'), ('quad', 'q'), ('single', 'f')]:
            if self.cfg['with_%s_prec' % prec]:

                # precision-specific binaries
                extra_files.append('bin/fftw%s-wisdom' % letter)

                # precision-specific .f03 header files
                inc_f03 = 'include/fftw3%s.f03' % letter
                if prec == 'single':
                    # no separate .f03 header file for single/double precision
                    inc_f03 = 'include/fftw3.f03'
                extra_files.append(inc_f03)

                # libraries, one for each precision and variant (if enabled)
                for variant in ['', 'mpi', 'openmp', 'threads']:
                    if variant == 'openmp':
                        suff = '_omp'
                    elif variant == '':
                        suff = ''
                    else:
                        suff = '_' + variant

                    # MPI is not compatible with quad precision
                    if variant == '' or self.cfg['with_%s' % variant] and not (prec == 'quad' and variant == 'mpi'):
                        extra_files.append('lib/libfftw3%s%s.a' % (letter, suff))

        # some additional files to check for when MPI is enabled
        if self.cfg['with_mpi']:
            extra_files.extend(['include/fftw3-mpi.f03', 'include/fftw3-mpi.h'])
            if self.cfg['with_long_double_prec']:
                extra_files.append('include/fftw3l-mpi.f03')

        custom_paths['files'].extend(nub(extra_files))

        super(EB_FFTW, self).sanity_check_step(custom_paths=custom_paths)
