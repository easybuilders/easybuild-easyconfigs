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
EasyBuild support for building and installing WRF-Fire, implemented as an easyblock

author: Kenneth Hoste (HPC-UGent)
"""
import os

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
from easybuild.tools.filetools import apply_regex_substitutions, change_dir, patch_perl_script_autoflush
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd, run_cmd_qa


class EB_WRF_minus_Fire(EasyBlock):
    """Support for building/installing WRF-Fire."""

    @staticmethod
    def extra_options():
        """Custom easyconfig parameters for WRF-Fire."""
        extra_vars = {
            'buildtype': [None, "Specify the type of build (serial, smpar (OpenMP), " \
                                "dmpar (MPI), dm+sm (hybrid OpenMP/MPI)).", MANDATORY],
            'runtest': [True, "Build and run WRF tests", CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Add extra config options specific to WRF."""
        super(EB_WRF_minus_Fire, self).__init__(*args, **kwargs)

        self.build_in_installdir = True

    def extract_step(self):
        """Extract WRF-Fire sources."""
        self.cfg.update('unpack_options', '--strip-components=1')
        super(EB_WRF_minus_Fire, self).extract_step()

    def configure_step(self):
        """Custom configuration procedure for WRF-Fire."""

        comp_fam = self.toolchain.comp_family()

        # define $NETCDF* for netCDF dependency
        netcdf_fortran = get_software_root('netCDF-Fortran')
        if netcdf_fortran:
            env.setvar('NETCDF', netcdf_fortran)
        else:
            raise EasyBuildError("Required dependendy netCDF-Fortran is missing")

        # define $PHDF5 for parallel HDF5 dependency
        hdf5 = get_software_root('HDF5')
        if hdf5 and os.path.exists(os.path.join(hdf5, 'bin', 'h5pcc')):
            env.setvar('PHDF5', hdf5)

        # first, configure WRF part
        change_dir(os.path.join(self.cfg['start_dir'], 'WRFV3'))

        # instruct WRF-Fire to create netCDF v4 output files
        env.setvar('WRFIO_NETCDF4_FILE_SUPPORT', '1')

        # patch arch/Config_new.pl script, so that run_cmd_qa receives all output to answer questions
        patch_perl_script_autoflush(os.path.join('arch', 'Config_new.pl'))

        # determine build type option to look for
        known_build_type_options = {
            toolchain.INTELCOMP: "Linux x86_64 i486 i586 i686, ifort compiler with icc",
            toolchain.GCC: "x86_64 Linux, gfortran compiler with gcc",
            toolchain.PGI: "Linux x86_64, PGI compiler with pgcc",
        }
        build_type_option = known_build_type_options.get(comp_fam)
        if build_type_option is None:
            raise EasyBuildError("Don't know which WPS configure option to select for compiler family %s", comp_fam)

        build_type_question = "\s*(?P<nr>[0-9]+).\s*%s\s*\(%s\)" % (build_type_option, self.cfg['buildtype'])
        qa = {
            "Compile for nesting? (1=basic, 2=preset moves, 3=vortex following) [default 1]:": '1',
        }
        std_qa = {
            # named group in match will be used to construct answer
            r"%s.*\n(.*\n)*Enter selection\s*\[[0-9]+-[0-9]+\]\s*:" % build_type_question: '%(nr)s',
        }
        run_cmd_qa('./configure', qa, std_qa=std_qa, log_all=True, simple=True)

        cpp_flag = None
        if comp_fam == toolchain.INTELCOMP:
            cpp_flag = '-fpp'
        elif comp_fam == toolchain.GCC:
            cpp_flag = '-cpp'
        else:
            raise EasyBuildError("Don't know which flag to use to specify that Fortran files were preprocessed")

        # patch configure.wrf to get things right
        comps = {
            'CFLAGS_LOCAL': os.getenv('CFLAGS'),
            'DM_FC': os.getenv('MPIF90'),
            'DM_CC': "%s -DMPI2_SUPPORT" % os.getenv('MPICC'),
            'FCOPTIM': os.getenv('FFLAGS'),
            # specify that Fortran files have been preprocessed with cpp,
            # see http://forum.wrfforum.com/viewtopic.php?f=5&t=6086
            'FORMAT_FIXED': "-FI %s" % cpp_flag,
            'FORMAT_FREE': "-FR %s" % cpp_flag,
        }
        regex_subs = [(r"^(%s\s*=\s*).*$" % k, r"\1 %s" % v) for (k, v) in comps.items()]
        apply_regex_substitutions('configure.wrf', regex_subs)

        # also configure WPS part
        change_dir(os.path.join(self.cfg['start_dir'], 'WPS'))

        # patch arch/Config_new.pl script, so that run_cmd_qa receives all output to answer questions
        patch_perl_script_autoflush(os.path.join('arch', 'Config.pl'))

        # determine build type option to look for
        known_build_type_options = {
            toolchain.INTELCOMP: "PC Linux x86_64, Intel compiler",
            toolchain.GCC: "PC Linux x86_64, g95 compiler",
            toolchain.PGI: "PC Linux x86_64 (IA64 and Opteron), PGI compiler 5.2 or higher",
        }
        build_type_option = known_build_type_options.get(comp_fam)
        if build_type_option is None:
            raise EasyBuildError("Don't know which WPS configure option to select for compiler family %s", comp_fam)

        known_wps_build_types = {
            'dmpar': 'DM parallel',
            'smpar': 'serial',
        }
        wps_build_type = known_wps_build_types.get(self.cfg['buildtype'])
        if wps_build_type is None:
            raise EasyBuildError("Don't know which WPS build type to pick for '%s'", self.cfg['builddtype'])

        build_type_question = "\s*(?P<nr>[0-9]+).\s*%s.*%s(?!NO GRIB2)" % (build_type_option, wps_build_type)
        std_qa = {
            # named group in match will be used to construct answer
            r"%s.*\n(.*\n)*Enter selection\s*\[[0-9]+-[0-9]+\]\s*:" % build_type_question: '%(nr)s',
        }
        run_cmd_qa('./configure', {}, std_qa=std_qa, log_all=True, simple=True)

        # patch configure.wps to get things right
        comps = {
            'CC': '%s %s' % (os.getenv('MPICC'), os.getenv('CFLAGS')),
            'FC': '%s %s' % (os.getenv('MPIF90'), os.getenv('F90FLAGS'))
        }
        regex_subs = [(r"^(%s\s*=\s*).*$" % k, r"\1 %s" % v) for (k, v) in comps.items()]
        # specify that Fortran90 files have been preprocessed with cpp
        regex_subs.extend([
            (r"^(F77FLAGS\s*=\s*)", r"\1 %s " % cpp_flag),
            (r"^(FFLAGS\s*=\s*)", r"\1 %s " % cpp_flag),
        ])
        apply_regex_substitutions('configure.wps', regex_subs)

    def build_step(self):
        """Custom build procedure for WRF-Fire."""

        cmd = './compile'
        if self.cfg['parallel']:
            cmd += " -j %d" % self.cfg['parallel']

        # first, build WRF part
        change_dir(os.path.join(self.cfg['start_dir'], 'WRFV3'))
        (out, ec) = run_cmd(cmd + ' em_fire', log_all=True, simple=False, log_ok=True)

        # next, build WPS part
        change_dir(os.path.join(self.cfg['start_dir'], 'WPS'))
        (out, ec) = run_cmd('./compile', log_all=True, simple=False, log_ok=True)

    def test_step(self):
        """Custom built-in test procedure for WRF-Fire."""
        if self.cfg['runtest']:
            change_dir(os.path.join(self.cfg['start_dir'], 'WRFV3', 'test', 'em_fire', 'hill'))

            if self.cfg['buildtype'] in ['dmpar', 'smpar', 'dm+sm']:
                test_cmd = "ulimit -s unlimited && %s && %s" % (self.toolchain.mpi_cmd_for("./ideal.exe", 1),
                                                                self.toolchain.mpi_cmd_for("./wrf.exe", 2))
            else:
                test_cmd = "ulimit -s unlimited && ./ideal.exe && ./wrf.exe"
            run_cmd(test_cmd, simple=True, log_all=True, log_ok=True)

    # building/installing is done in build_step, so we can run tests
    def install_step(self):
        """Building was done in install dir, so nothing to do in install_step."""
        pass

    def sanity_check_step(self):
        """Custom sanity check for WRF-Fire."""
        custom_paths = {
            'files': [os.path.join('WRFV3', 'main', f) for f in ['ideal.exe', 'libwrflib.a', 'wrf.exe']] +
                     [os.path.join('WPS', f) for f in ['geogrid.exe', 'metgrid.exe', 'ungrib.exe']],
            'dirs': [os.path.join('WRFV3', d) for d in ['main', 'run']],
        }
        super(EB_WRF_minus_Fire, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Custom guesses for generated WRF-Fire module file."""
        wrf_maindir = os.path.join('WRFV3', 'main')
        return {
            'LD_LIBRARY_PATH': [wrf_maindir],
            'PATH': [wrf_maindir, 'WPS'],
        }

    def make_module_extra(self):
        """Add netCDF environment variables to module file."""
        txt = super(EB_WRF_minus_Fire, self).make_module_extra()
        netcdf_fortran = get_software_root('netCDF-Fortran')
        if netcdf_fortran:
            txt += self.module_generator.set_environment('NETCDF', netcdf_fortran)
        return txt
