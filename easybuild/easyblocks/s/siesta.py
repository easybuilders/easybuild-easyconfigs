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
EasyBuild support for building and installing Siesta, implemented as an easyblock

@author: Miguel Dias Costa (National University of Singapore)
@author: Ake Sandgren (Umea University)
"""
import os
import stat

import easybuild.tools.toolchain as toolchain
from distutils.version import LooseVersion
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import adjust_permissions, apply_regex_substitutions, change_dir, copy_dir, copy_file, mkdir
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd


class EB_Siesta(ConfigureMake):
    """
    Support for building/installing Siesta.
    - avoid parallel build for older versions
    """

    @staticmethod
    def extra_options(extra_vars=None):
        """Define extra options for Siesta"""
        extra = {
            'with_transiesta': [True, "Build transiesta", CUSTOM],
            'with_utils': [True, "Build all utils", CUSTOM],
        }
        return ConfigureMake.extra_options(extra_vars=extra)

    def configure_step(self):
        """
        Custom configure and build procedure for Siesta.
        - There are two main builds to do, siesta and transiesta
        - In addition there are multiple support tools to build
        """

        start_dir = self.cfg['start_dir']
        obj_dir = os.path.join(start_dir, 'Obj')
        arch_make = os.path.join(obj_dir, 'arch.make')
        bindir = os.path.join(start_dir, 'bin')

        par = ''
        if LooseVersion(self.version) >= LooseVersion('4.1'):
            par = '-j %s' % self.cfg['parallel']

        # enable OpenMP support if desired
        env_var_suff = ''
        if self.toolchain.options.get('openmp', None):
            env_var_suff = '_MT'

        scalapack = os.environ['LIBSCALAPACK' + env_var_suff]
        blacs = os.environ['LIBSCALAPACK' + env_var_suff]
        lapack = os.environ['LIBLAPACK' + env_var_suff]
        blas = os.environ['LIBBLAS' + env_var_suff]
        if get_software_root('imkl') or get_software_root('FFTW'):
            fftw = os.environ['LIBFFT' + env_var_suff]
        else:
            fftw = None

        regex_newlines = []
        regex_subs = [
            ('dc_lapack.a', ''),
            (r'^NETCDF_INTERFACE\s*=.*$', ''),
            ('libsiestaBLAS.a', ''),
            ('libsiestaLAPACK.a', ''),
            # Needed here to allow 4.1-b1 to be built with openmp
            (r"^(LDFLAGS\s*=).*$", r"\1 %s %s" % (os.environ['FCFLAGS'], os.environ['LDFLAGS'])),
        ]

        netcdff_loc = get_software_root('netCDF-Fortran')
        if netcdff_loc:
            # Needed for gfortran at least
            regex_newlines.append((r"^(ARFLAGS_EXTRA\s*=.*)$", r"\1\nNETCDF_INCFLAGS = -I%s/include" % netcdff_loc))

        if fftw:
            fft_inc, fft_lib = os.environ['FFT_INC_DIR'], os.environ['FFT_LIB_DIR']
            fppflags = r"\1\nFFTW_INCFLAGS = -I%s\nFFTW_LIBS = -L%s %s" % (fft_inc, fft_lib, fftw)
            regex_newlines.append((r'(FPPFLAGS\s*=.*)$', fppflags))

        # Make a temp installdir during the build of the various parts
        mkdir(bindir)

        # change to actual build dir
        change_dir(obj_dir)

        # Populate start_dir with makefiles
        run_cmd(os.path.join(start_dir, 'Src', 'obj_setup.sh'), log_all=True, simple=True, log_output=True)

        if LooseVersion(self.version) < LooseVersion('4.1-b2'):
            # MPI?
            if self.toolchain.options.get('usempi', None):
                self.cfg.update('configopts', '--enable-mpi')

            # BLAS and LAPACK
            self.cfg.update('configopts', '--with-blas="%s"' % blas)
            self.cfg.update('configopts', '--with-lapack="%s"' % lapack)

            # ScaLAPACK (and BLACS)
            self.cfg.update('configopts', '--with-scalapack="%s"' % scalapack)
            self.cfg.update('configopts', '--with-blacs="%s"' % blacs)

            # NetCDF-Fortran
            if netcdff_loc:
                self.cfg.update('configopts', '--with-netcdf=-lnetcdff')

            # Configure is run in obj_dir, configure script is in ../Src
            super(EB_Siesta, self).configure_step(cmd_prefix='../Src/')

            if LooseVersion(self.version) > LooseVersion('4.0'):
                regex_subs_Makefile = [
                    (r'CFLAGS\)-c', r'CFLAGS) -c'),
                ]
                apply_regex_substitutions('Makefile', regex_subs_Makefile)

        else: # there's no configure on newer versions

            if self.toolchain.comp_family() in [toolchain.INTELCOMP]:
                copy_file(os.path.join(obj_dir, 'intel.make'), arch_make)
            elif self.toolchain.comp_family() in [toolchain.GCC]:
                copy_file(os.path.join(obj_dir, 'gfortran.make'), arch_make)
            else:
                raise EasyBuildError("There is currently no support for compiler: %s", self.toolchain.comp_family())

            if self.toolchain.options.get('usempi', None):
                regex_subs.extend([
                    (r"^(CC\s*=\s*).*$", r"\1%s" % os.environ['MPICC']),
                    (r"^(FC\s*=\s*).*$", r"\1%s" % os.environ['MPIF90']),
                    (r"^(FPPFLAGS\s*=.*)$", r"\1 -DMPI"),
                ])
                regex_newlines.append((r"^(FPPFLAGS\s*=.*)$", r"\1\nMPI_INTERFACE = libmpi_f90.a\nMPI_INCLUDE = ."))
                complibs = scalapack
            else:
                complibs = lapack

            regex_subs.extend([
                (r"^(LIBS\s*=\s).*$", r"\1 %s" % complibs),
                # Needed for a couple of the utils
                (r"^(FFLAGS\s*=\s*).*$", r"\1 -fPIC %s" % os.environ['FCFLAGS']),
            ])
            regex_newlines.append((r"^(COMP_LIBS\s*=.*)$", r"\1\nWXML = libwxml.a"))

            if netcdff_loc:
                regex_subs.extend([
                    (r"^(LIBS\s*=.*)$", r"\1 $(NETCDF_LIBS)"),
                    (r"^(FPPFLAGS\s*=.*)$", r"\1 -DCDF"),
                ])
                regex_newlines.append((r"^(COMP_LIBS\s*=.*)$", r"\1\nNETCDF_LIBS = -lnetcdff"))

        apply_regex_substitutions(arch_make, regex_subs)

        # individually apply substitutions that add lines
        for regex_nl in regex_newlines:
            apply_regex_substitutions(arch_make, [regex_nl])

        run_cmd('make %s' % par, log_all=True, simple=True, log_output=True)

        # Put binary in temporary install dir
        copy_file(os.path.join(obj_dir, 'siesta'), bindir)

        if self.cfg['with_utils']:
            # Make the utils
            change_dir(os.path.join(start_dir, 'Util'))

            # clean_all.sh might be missing executable bit...
            adjust_permissions('./clean_all.sh', stat.S_IXUSR, recursive=False, relative=True)
            run_cmd('./clean_all.sh', log_all=True, simple=True, log_output=True)

            if LooseVersion(self.version) >= LooseVersion('4.1'):
                regex_subs_TS = [
                    (r"^default:.*$", r""),
                    (r"^EXE\s*=.*$", r""),
                    (r"^(include\s*..ARCH_MAKE.*)$", r"EXE=tshs2tshs\ndefault: $(EXE)\n\1"),
                    (r"^(INCFLAGS.*)$", r"\1 -I%s" % obj_dir),
                ]

                makefile = os.path.join(start_dir, 'Util', 'TS', 'tshs2tshs', 'Makefile')
                apply_regex_substitutions(makefile, regex_subs_TS)

            # SUFFIX rules in wrong place
            regex_subs_suffix = [
                (r'^(\.SUFFIXES:.*)$', r''),
                (r'^(include\s*\$\(ARCH_MAKE\).*)$', r'\1\n.SUFFIXES:\n.SUFFIXES: .c .f .F .o .a .f90 .F90'),
            ]
            makefile = os.path.join(start_dir, 'Util', 'Sockets', 'Makefile')
            apply_regex_substitutions(makefile, regex_subs_suffix)
            makefile = os.path.join(start_dir, 'Util', 'SiestaSubroutine', 'SimpleTest', 'Src', 'Makefile')
            apply_regex_substitutions(makefile, regex_subs_suffix)

            regex_subs_UtilLDFLAGS = [
                (r'(\$\(FC\)\s*-o\s)', r'$(FC) %s %s -o ' % (os.environ['FCFLAGS'], os.environ['LDFLAGS'])),
            ]
            makefile = os.path.join(start_dir, 'Util', 'Optimizer', 'Makefile')
            apply_regex_substitutions(makefile, regex_subs_UtilLDFLAGS)
            makefile = os.path.join(start_dir, 'Util', 'JobList', 'Src', 'Makefile')
            apply_regex_substitutions(makefile, regex_subs_UtilLDFLAGS)

            run_cmd('./build_all.sh', log_all=True, simple=True, log_output=True)

            # Now move all the built utils to the temp installdir
            expected_utils = [
                'Bands/eigfat2plot',
                'CMLComp/ccViz',
                'Contrib/APostnikov/eig2bxsf', 'Contrib/APostnikov/rho2xsf',
                'Contrib/APostnikov/vib2xsf', 'Contrib/APostnikov/fmpdos',
                'Contrib/APostnikov/xv2xsf', 'Contrib/APostnikov/md2axsf',
                'COOP/mprop', 'COOP/fat',
                'Denchar/Src/denchar',
                'DensityMatrix/dm2cdf', 'DensityMatrix/cdf2dm',
                'Eig2DOS/Eig2DOS',
                'Gen-basis/ioncat', 'Gen-basis/gen-basis',
                'Grid/cdf2grid', 'Grid/cdf_laplacian', 'Grid/cdf2xsf',
                'Grid/grid2cube',
                'Grid/grid_rotate', 'Grid/g2c_ng', 'Grid/grid2cdf', 'Grid/grid2val',
                'Helpers/get_chem_labels',
                'HSX/hs2hsx', 'HSX/hsx2hs',
                'JobList/Src/getResults', 'JobList/Src/countJobs',
                'JobList/Src/runJobs', 'JobList/Src/horizontal',
                'Macroave/Src/macroave',
                'ON/lwf2cdf',
                'Optimizer/simplex', 'Optimizer/swarm',
                'pdosxml/pdosxml',
                'Projections/orbmol_proj',
                'SiestaSubroutine/FmixMD/Src/driver',
                'SiestaSubroutine/FmixMD/Src/para',
                'SiestaSubroutine/FmixMD/Src/simple',
                'STM/simple-stm/plstm', 'STM/ol-stm/Src/stm',
                'VCA/mixps', 'VCA/fractional',
                'Vibra/Src/vibra', 'Vibra/Src/fcbuild',
                'WFS/info_wfsx', 'WFS/wfsx2wfs',
                'WFS/readwfx', 'WFS/wfsnc2wfsx', 'WFS/readwf', 'WFS/wfs2wfsx',
            ]

            if LooseVersion(self.version) <= LooseVersion('4.0'):
                expected_utils.extend([
                    'Bands/new.gnubands',
                    'TBTrans/tbtrans',
                ])

            if LooseVersion(self.version) >= LooseVersion('4.0'):
                expected_utils.extend([
                    'SiestaSubroutine/ProtoNEB/Src/protoNEB',
                    'SiestaSubroutine/SimpleTest/Src/simple_pipes_parallel',
                    'SiestaSubroutine/SimpleTest/Src/simple_pipes_serial',
                    'Sockets/f2fmaster', 'Sockets/f2fslave',
                ])

            if LooseVersion(self.version) >= LooseVersion('4.1'):
                expected_utils.extend([
                    'Bands/gnubands',
                    'Grimme/fdf2grimme',
                    'SpPivot/pvtsp',
                    'TS/ts2ts/ts2ts', 'TS/tshs2tshs/tshs2tshs', 'TS/TBtrans/tbtrans',
                ])

            for util in expected_utils:
                copy_file(os.path.join(start_dir, 'Util', util), bindir)

        if self.cfg['with_transiesta']:
            # Build transiesta
            change_dir(obj_dir)

            run_cmd('make clean', log_all=True, simple=True, log_output=True)
            run_cmd('make %s transiesta' % par, log_all=True, simple=True, log_output=True)

            copy_file(os.path.join(obj_dir, 'transiesta'), bindir)

    def build_step(self):
        """No build step for Siesta."""
        pass

    def install_step(self):
        """Custom install procedure for Siesta: copy binaries."""
        bindir = os.path.join(self.installdir, 'bin')
        copy_dir(os.path.join(self.cfg['start_dir'], 'bin'), bindir)

    def sanity_check_step(self):
        """Custom sanity check for Siesta."""

        bins = ['bin/siesta']

        if self.cfg['with_transiesta']:
            bins.append('bin/transiesta')

        if self.cfg['with_utils']:
            bins.append('bin/denchar')

        custom_paths = {
            'files': bins,
            'dirs': [],
        }
        custom_commands = []
        if self.toolchain.options.get('usempi', None):
            # make sure Siesta was indeed built with support for running in parallel
            custom_commands.append("echo 'SystemName test' | mpirun -np 2 siesta 2>/dev/null | grep PARALLEL")

        super(EB_Siesta, self).sanity_check_step(custom_paths=custom_paths, custom_commands=custom_commands)
