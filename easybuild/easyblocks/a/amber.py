##
# Copyright 2009-2017 Ghent University
# Copyright 2015-2017 Stanford University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
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
EasyBuild support for Amber, implemented as an easyblock

Original author: Benjamin Roberts (The University of Auckland)
Modified by Stephane Thiell (Stanford University) for Amber14
Enhanced/cleaned up by Kenneth Hoste (HPC-UGent)
"""
import os

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.easyblocks.generic.pythonpackage import det_pylibdir
from easybuild.framework.easyconfig import CUSTOM, MANDATORY, BUILD
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd


class EB_Amber(ConfigureMake):
    """Easyblock for building and installing Amber"""

    @staticmethod
    def extra_options(extra_vars=None):
        """Extra easyconfig parameters specific to ConfigureMake."""
        extra_vars = dict(ConfigureMake.extra_options(extra_vars))
        extra_vars.update({
            # 'Amber': [True, "Build Amber in addition to AmberTools", CUSTOM],
            'patchlevels': ["latest", "(AmberTools, Amber) updates to be applied", CUSTOM],
            # The following is necessary because some patches to the Amber update
            # script update the update script itself, in which case it will quit
            # and insist on being run again. We don't know how many times will
            # be needed, but the number of times is patchlevel specific.
            'patchruns': [1, "Number of times to run Amber's update script before building", CUSTOM],
            # enable testing by default
            'runtest': [True, "Run tests after each build", CUSTOM],
        })
        return ConfigureMake.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Easyblock constructor: initialise class variables."""
        super(EB_Amber, self).__init__(*args, **kwargs)
        self.build_in_installdir = True
        self.pylibdir = None

        self.with_cuda = False
        self.with_mpi = False

        env.setvar('AMBERHOME', self.installdir)

    def extract_step(self):
        """Extract sources; strip off parent directory during unpack"""
        self.cfg.update('unpack_options', "--strip-components=1")
        super(EB_Amber, self).extract_step()

    def patch_step(self, *args, **kwargs):
        """Patch Amber using 'update_amber' tool, prior to applying listed patch files (if any)."""

        if self.cfg['patchlevels'] == "latest":
            cmd = "./update_amber --update"
            # Run as many times as specified. It is the responsibility
            # of the easyconfig author to get this right, especially if
            # he or she selects "latest". (Note: "latest" is not
            # recommended for this reason and others.)
            for _ in range(self.cfg['patchruns']):
                run_cmd(cmd, log_all=True)
        else:
            for (tree, patch_level) in zip(['AmberTools', 'Amber'], self.cfg['patchlevels']):
                if patch_level == 0:
                    continue
                cmd = "./update_amber --update-to %s/%s" % (tree, patch_level)
                # Run as many times as specified. It is the responsibility
                # of the easyconfig author to get this right.
                for _ in range(self.cfg['patchruns']):
                    run_cmd(cmd, log_all=True)

        super(EB_Amber, self).patch_step(*args, **kwargs)

    def configure_step(self):
        """Configuring Amber is done in install step."""
        pass

    def build_step(self):
        """Building Amber is done in install step."""
        pass

    def test_step(self):
        """Testing Amber build is done in install step."""
        pass

    def install_step(self):
        """Custom build, test & install procedure for Amber."""

        # unset $LIBS since it breaks the build
        env.unset_env_vars(['LIBS'])

        # define environment variables for MPI, BLAS/LAPACK & dependencies
        mklroot = get_software_root('imkl')
        if mklroot:
            env.setvar('MKL_HOME', mklroot)

        mpiroot = get_software_root(self.toolchain.MPI_MODULE_NAME[0])
        if mpiroot and self.toolchain.options.get('usempi', None):
            env.setvar('MPI_HOME', mpiroot)
            self.with_mpi = True

        common_configopts = [self.cfg['configopts'], '--no-updates', '-static', '-noX11']

        netcdfroot = get_software_root('netCDF')
        if netcdfroot:
            common_configopts.extend(["--with-netcdf", netcdfroot])

        netcdf_fort_root = get_software_root('netCDF-Fortran')
        if netcdf_fort_root:
            common_configopts.extend(["--with-netcdf-fort", netcdf_fort_root])

        pythonroot = get_software_root('Python')
        if pythonroot:
            common_configopts.extend(["--with-python", os.path.join(pythonroot, 'bin', 'python')])

            self.pylibdir = det_pylibdir()
            pythonpath = os.environ.get('PYTHONPATH', '')
            env.setvar('PYTHONPATH', os.pathsep.join([os.path.join(self.installdir, self.pylibdir), pythonpath]))

        comp_fam = self.toolchain.comp_family()
        if comp_fam == toolchain.INTELCOMP:
            comp_str = 'intel'

        elif comp_fam == toolchain.GCC:
            comp_str = 'gnu'

        else:
            raise EasyBuildError("Don't know how to compile with compiler family '%s' -- check EasyBlock?", comp_fam)

        # compose list of build targets
        build_targets = [('', 'test')]

        if self.with_mpi:
            build_targets.append(('-mpi', 'test.parallel'))
            # hardcode to 4 MPI processes, minimal required to run all tests
            env.setvar('DO_PARALLEL', 'mpirun -np 4')

        cudaroot = get_software_root('CUDA')
        if cudaroot:
            env.setvar('CUDA_HOME', cudaroot)
            self.with_cuda = True
            build_targets.append(('-cuda', 'test.cuda'))
            if self.with_mpi:
                build_targets.append(("-cuda -mpi", 'test.cuda_parallel'))

        ld_lib_path = os.environ.get('LD_LIBRARY_PATH', '')
        env.setvar('LD_LIBRARY_PATH', os.pathsep.join([os.path.join(self.installdir, 'lib'), ld_lib_path]))

        for flag, testrule in build_targets:
            # configure
            cmd = "%s ./configure %s" % (self.cfg['preconfigopts'], ' '.join(common_configopts + [flag, comp_str]))
            (out, _) = run_cmd(cmd, log_all=True, simple=False)

            # build in situ using 'make install'
            # note: not 'build'
            super(EB_Amber, self).install_step()

            # test
            if self.cfg['runtest']:
                run_cmd("make %s" % testrule, log_all=True, simple=False)

            # clean, overruling the normal 'build'
            run_cmd("make clean")

    def sanity_check_step(self):
        """Custom sanity check for Amber."""
        binaries = ['pmemd', 'sander', 'tleap']
        if self.with_cuda:
            binaries.append('pmemd.cuda')
            if self.with_mpi:
                binaries.append('pmemd.cuda.MPI')
        if self.with_mpi:
            binaries.extend(['pmemd.MPI', 'sander.MPI'])

        custom_paths = {
            'files': [os.path.join(self.installdir, 'bin', binary) for binary in binaries],
            'dirs': [],
        }
        super(EB_Amber, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Add module entries specific to Amber/AmberTools"""
        txt = super(EB_Amber, self).make_module_extra()

        txt += self.module_generator.set_environment('AMBERHOME', self.installdir)
        if self.pylibdir:
            txt += self.module_generator.prepend_paths('PYTHONPATH', self.pylibdir)

        return txt
