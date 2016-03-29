##
# Copyright 2009-2015 Ghent University
# Copyright 2015-2016 Stanford University
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
"""
import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM, MANDATORY, BUILD
from easybuild.tools.build_log import EasyBuildError
import easybuild.tools.environment as env
from easybuild.tools.run import run_cmd
from easybuild.tools.modules import get_software_root, get_software_version
import easybuild.tools.toolchain as toolchain

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
        })
        return ConfigureMake.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        super(EB_Amber, self).__init__(*args, **kwargs)
        self.already_extracted = False
        self.build_in_installdir = True

    def extract_step(self):
        """Only extract from the tarball if this has not already been done."""
        if not self.already_extracted:
            # unpack_options is a string, not an array; can't use append
            self.cfg['unpack_options'] += " --strip-components=1"
            super(EB_Amber, self).extract_step()
            self.already_extracted = True

    def patch_step(self, **kw):
        env.setvar('AMBERHOME', self.installdir)
        if self.cfg['patchlevels'] == "latest":
            cmd = "./update_amber --update"
            # Run as many times as specified. It is the responsibility
            # of the easyconfig author to get this right, especially if
            # he or she selects "latest". (Note: "latest" is not
            # recommended for this reason and others.)
            for i in range(self.cfg['patchruns']):
                run_cmd(cmd, log_all=True)
        else:
            for (tree, patch_level) in zip(['AmberTools', 'Amber'], self.cfg['patchlevels']):
                if patch_level == 0:
                    continue
                cmd = "./update_amber --update-to %s/%s" % (tree, patch_level)
                # Run as many times as specified. It is the responsibility
                # of the easyconfig author to get this right.
                for i in range(self.cfg['patchruns']):
                    run_cmd(cmd, log_all=True)
        return super(EB_Amber, self).patch_step(**kw)

    def configure_step(self):
        # We need a special configure_step as Amber does not recognise --prefix
        cmd = "%(preconfigopts)s ./configure %(configopts)s" % {
                'preconfigopts': self.cfg['preconfigopts'],
                'configopts': self.cfg['configopts']
            }
        (out, _) = run_cmd(cmd, log_all=True, simple=False)
        return out

    def build_step(self):

        # Set the AMBERHOME environment variable
        env.setvar('AMBERHOME', self.installdir)
        try:
            os.chdir(self.installdir)
        except OSError, err:
            raise EasyBuildError("Could not chdir to {0}: {1}".format(self.installdir, err))

        # Kenneth Hoste recommends making sure the LIBS env var is unset
        env.unset_env_vars(['LIBS'])

        # Set some other environment variables
        for mathlib in ['imkl']:
            mklroot = get_software_root(mathlib)
            if mklroot:
                env.setvar('MKL_HOME', mklroot)

        for mpilib in ['impi', 'OpenMPI', 'MVAPICH2', 'MPICH2']:
            mpiroot = get_software_root(mpilib)
            if mpiroot:
                env.setvar('MPI_HOME', mpiroot)

        common_configopts = ["--no-updates", "-static", "-noX11"]
        netcdfroot = get_software_root('netCDF')
        if netcdfroot:
            common_configopts.append("--with-netcdf")
            common_configopts.append(netcdfroot)
        netcdf_fort_root = get_software_root('netCDF-Fortran')
        if netcdf_fort_root:
            common_configopts.append("--with-netcdf-fort")
            common_configopts.append(netcdf_fort_root)
        pythonroot = get_software_root('Python')
        if pythonroot:
            common_configopts.append("--with-python")
            common_configopts.append(os.path.join(pythonroot, 'bin', 'python'))

        do_cuda = False
        compilerstring = ''
        if self.toolchain.comp_family() == toolchain.INTELCOMP:
            do_cuda = True
            compilerstring = 'intel'
        elif self.toolchain.comp_family() == toolchain.GCC:
            compilerstring = 'gnu'
        else:
            raise EasyBuildError("Don't know how to compile with compiler family {0} -- check EasyBlock?".format(self.toolchain.comp_family()))

        buildtargets = [('', 'test')]
        if self.toolchain.options.get('usempi', None):
            buildtargets.append(("-mpi", 'test.parallel'))
            env.setvar('DO_PARALLEL', 'mpirun -np 4')
            if do_cuda:
                buildtargets.append(("-cuda -mpi", 'test.cuda_parallel'))

        if do_cuda:
            cudaroot = get_software_root('CUDA')
            if cudaroot:
                env.setvar('CUDA_HOME', cudaroot)
                buildtargets.append(('-cuda', 'test.cuda'))

        pythonpath = os.environ.get('PYTHONPATH', '')
        env.setvar('PYTHONPATH', ':'.join([os.path.join(self.installdir, "lib/python2.7/site-packages"), pythonpath]))

        ld_lib_path = os.environ.get('LD_LIBRARY_PATH', '')
        env.setvar('LD_LIBRARY_PATH', ':'.join([os.path.join(self.installdir, "lib"), ld_lib_path]))

        for flag, testrule in buildtargets:
            # Configure
            self.cfg['configopts'] = ' '.join(common_configopts + [flag, compilerstring])
            self.configure_step()

            # Build in situ using 'make install'
            # Note: not "build"
            super(EB_Amber, self).install_step()

            # Test
            self.cfg['runtest'] = testrule
            super(EB_Amber, self).test_step()

            # Clean, overruling the normal "build"
            self.cfg['prebuildopts'] = ''
            self.cfg['buildopts'] = 'clean'
            super(EB_Amber, self).build_step()

    def test_step(self):
        pass

    def install_step(self):
        """In Amber, installation is conflated with building,
        so that 'make install' is done during the build step."""
        pass

    def sanity_check_step(self):
        """Custom sanity check for Amber."""
        files = ["tleap", "sander", "sander.MPI", "pmemd", "pmemd.MPI", "pmemd.cuda", "pmemd.cuda.MPI"]
        dirs = ["."]
        custom_paths = {
            'files': [os.path.join(self.installdir, "bin", file) for file in files],
            'dirs': [os.path.join(self.installdir, dir) for dir in dirs]
        }
        super(EB_Amber, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):

        guesses = super(EB_Amber, self).make_module_req_guess()

        guesses.update({
            'PATH': ['bin'],
            'LD_LIBRARY_PATH': ['lib'],
        })

        return guesses

    def make_module_extra(self):
        """Add module entries specific to Amber/AmberTools"""
        txt = super(EB_Amber, self).make_module_extra()
        txt += self.module_generator.set_environment('AMBERHOME', self.installdir)
        txt += self.module_generator.load_module("CUDA/%s" % get_software_version("CUDA"))
        txt += self.module_generator.prepend_paths('PYTHONPATH', ["lib/python2.7/site-packages"])
        return txt
