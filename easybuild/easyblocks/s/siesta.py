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
EasyBuild support for building and installing Siesta, implemented as an easyblock

@author: Ake Sandgren (Umea University)
"""
import os
import re
import shutil
import stat
import tempfile

import easybuild.tools.config as config
import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from distutils.version import LooseVersion
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import adjust_permissions, apply_regex_substitutions, copy_file, mkdir, write_file
from easybuild.tools.modules import get_software_libdir, get_software_root, get_software_version
from easybuild.tools.run import run_cmd


class EB_Siesta(ConfigureMake):
    """
    Support for building/installing Siesta.
    - avoid parallel build, doesn't work
    """

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for Siesta."""
        super(EB_Siesta, self).__init__(*args, **kwargs)

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
        bindir = os.path.join(self.cfg['start_dir'], 'bin')

        netcdff_loc = get_software_root('NetCDF-Fortran')

        # enable OpenMP support if desired
        openmp = self.toolchain.options.get('openmp', None)
        if openmp:
            scalapack = os.environ['LIBSCALAPACK_MT']
            blacs = os.environ['LIBSCALAPACK_MT']
            lapack = os.environ['LIBLAPACK_MT']
            blas = os.environ['LIBBLAS_MT']
        else:
            scalapack = os.environ['LIBSCALAPACK']
            blacs = os.environ['LIBSCALAPACK']
            lapack = os.environ['LIBLAPACK']
            blas = os.environ['LIBBLAS']

        regex_subs = [
            ('dc_lapack.a', ''),
            (r'^NETCDF_INTERFACE\s*=.*$', ''),
            ('libsiestaBLAS.a', ''),
            ('libsiestaLAPACK.a', ''),
        ]

        # Make a temp installdir during the build of the various parts
        try:
            mkdir(bindir)
        except OSError, err:
            raise EasyBuildError("Failed to create temp installdir %s: %s", bindir, err)

        # change to actual build dir
        try:
            os.chdir(obj_dir)
        except OSError, err:
            raise EasyBuildError("Failed to change to build dir: %s", err)

        # Populate start_dir with makefiles
        run_cmd(os.path.join(start_dir, 'Src', 'obj_setup.sh'), log_all=True, simple=True, log_output=True)

        if LooseVersion(self.version) < LooseVersion("4.1-b2"):
            # MPI?
            if self.toolchain.options.get('usempi', None):
                self.cfg.update('configopts', '--enable-mpi')

            # BLAS and LAPACK
            self.cfg.update('configopts', '--with-blas="%s"' % blas)
            self.cfg.update('configopts', '--with-lapack="%s"' % lapack)

            # ScaLAPACK (and BLACS)
            self.cfg.update('configopts', '--with-scalapack="%s"' % scalapack)
            self.cfg.update('configopts', '--with-blacs="$%s"' % blacs)

            # NetCDF-Fortran
            if netcdff_loc:
                self.cfg.update('configopts', '--with-netcdf=-lnetcdff')

            super(EB_Siesta, self).configure_step(cmd_prefix='../Src/')

        else: # there's no configure on newer versions

            if self.toolchain.comp_family() in [toolchain.INTELCOMP]:
                copy_file(os.path.join(obj_dir, 'intel.make'), arch_make)
            else:
                copy_file(os.path.join(obj_dir, 'gfortran.make'), arch_make)

            if self.toolchain.options.get('usempi', None):
                regex_subs.extend([
                    (r"^(CC\s*=\s*).*$", r"\1%s" % os.environ['MPICC']),
                    (r"^(FC\s*=\s*).*$", r"\1%s" % os.environ['MPIF90']),
                    (r"^(FPPFLAGS\s*=.*)$", r"\1 -DMPI"),
                    (r"^(FPPFLAGS\s*=.*)$", r"\1\nMPI_INTERFACE = libmpi_f90.a\nMPI_INCLUDE = ."),
                ])
                complibs = scalapack
            else:
                complibs = lapack

            regex_subs.extend([
                (r"^(LIBS\s*=\s).*$", r"\1 %s" % complibs),
                # Needed for a couple of the utils
                (r"^(COMP_LIBS\s*=.*)$", r"\1\nWXML = libwxml.a"),
                (r"^(FFLAGS\s*=\s*).*$", r"\1 -fPIC %s" % os.environ['FCFLAGS']),
                (r"^(LDFLAGS\s*=).*$", r"\1 %s %s" % (os.environ['FCFLAGS'], os.environ['LDFLAGS'])),
            ])

            if netcdff_loc:
                regex_subs.extend([
                    (r"^(COMP_LIBS\s*=.*)$", r"\1\nNETCDF_LIBS = -lnetcdff"),
                    (r"^(LIBS\s*=.*)$", r"\1 $(NETCDF_LIBS)"),
                    (r"^(FPPFLAGS\s*=.*)$", r"\1 -DCDF"),
                ])

        apply_regex_substitutions(arch_make, regex_subs)

        run_cmd('make -j %s' % self.cfg['parallel'], log_all=True, simple=True, log_output=True)

        # Put binary in temporary install dir
        shutil.copy(os.path.join(self.cfg['start_dir'], 'Obj', 'siesta'),
                    bindir)

        if self.cfg['with_utils']:
            # Make the utils
            try:
                os.chdir(os.path.join(start_dir, 'Util'))
            except OSError, err:
                raise EasyBuildError("Failed to change to Util dir: %s", err)

            # clean_all.sh might be missing executable bit...
            adjust_permissions('./clean_all.sh', stat.S_IXUSR, recursive=False, relative=True)
            run_cmd('./clean_all.sh', log_all=True, simple=True, log_output=True)

            if LooseVersion(self.version) >= LooseVersion("4.0"):
                regex_subs_TS = [
                    (r"^default:.*$", r""),
                    (r"^EXE\s*=.*$", r""),
                    (r"^(include\s*..ARCH_MAKE.*)$", r"EXE=tshs2tshs\ndefault: $(EXE)\n\1"),
                    (r"^(INCFLAGS.*)$", r"\1 -I%s" % obj_dir),
                ]

                apply_regex_substitutions(os.path.join(self.cfg['start_dir'], 'Util', 'TS', 'tshs2tshs', 'Makefile'), regex_subs_TS)

            regex_subs_UtilLDFLAGS = [
                (r'(\$\(FC\)\s*-o\s)', r'$(FC) %s %s -o ' % (os.environ['FCFLAGS'], os.environ['LDFLAGS'])),
            ]
            apply_regex_substitutions(os.path.join(self.cfg['start_dir'], 'Util', 'Optimizer', 'Makefile'), regex_subs_UtilLDFLAGS)
            apply_regex_substitutions(os.path.join(self.cfg['start_dir'], 'Util', 'JobList', 'Src', 'Makefile'), regex_subs_UtilLDFLAGS)

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

            if LooseVersion(self.version) <= LooseVersion("4.0"):
                expected_utils.extend([
                    'Bands/new.gnubands',
                    'TBTrans/tbtrans',
                ])

            if LooseVersion(self.version) >= LooseVersion("4.0"):
                expected_utils.extend([
                    'SiestaSubroutine/ProtoNEB/Src/protoNEB',
                    'SiestaSubroutine/SimpleTest/Src/simple_pipes_parallel',
                    'SiestaSubroutine/SimpleTest/Src/simple_pipes_serial',
                    'Sockets/f2fmaster', 'Sockets/f2fslave',
                ])

            if LooseVersion(self.version) >= LooseVersion("4.1"):
                expected_utils.extend([
                    'Bands/gnubands',
                    'Grimme/fdf2grimme',
                    'SpPivot/pvtsp',
                    'TS/ts2ts/ts2ts', 'TS/tshs2tshs/tshs2tshs', 'TS/TBtrans/tbtrans',
                ])

            for f in expected_utils:
                shutil.copy(os.path.join(self.cfg['start_dir'], 'Util', f), bindir)

        if self.cfg['with_transiesta']:
            # Build transiesta
            try:
                os.chdir(obj_dir)
            except OSError, err:
                raise EasyBuildError("Failed to change back to Obj dir: %s", err)

            run_cmd('make clean', log_all=True, simple=True, log_output=True)
            run_cmd('make -j %s transiesta' % self.cfg['parallel'], log_all=True, simple=True, log_output=True)

            shutil.copy(os.path.join(self.cfg['start_dir'], 'Obj', 'transiesta'),
                        bindir)

    def build_step(self):
        """No build step for Siesta."""
        pass

    def install_step(self):
        """Custom install procedure for Siesta."""

        try:
            # binary
            bindir = os.path.join(self.installdir, 'bin')
            shutil.copytree(os.path.join(self.cfg['start_dir'], 'bin'), bindir)

        except OSError, err:
            raise EasyBuildError("Failed to install Siesta: %s", err)

    def sanity_check_step(self):
        """Custom sanity check for Siesta."""

        bins = ['bin/siesta']

        if self.cfg['with_transiesta']:
            bins.extend(['bin/transiesta'])

        if self.cfg['with_utils']:
            bins.extend(['bin/denchar'])

        custom_paths = {
            'files': bins,
            'dirs': [],
        }

        super(EB_Siesta, self).sanity_check_step(custom_paths=custom_paths)
