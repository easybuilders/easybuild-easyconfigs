##
# Copyright 2009-2012 Ghent University
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
EasyBuild support for building and installing NWChem, implemented as an easyblock
"""
import os
import shutil
import tempfile

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import mkdir, run_cmd
from easybuild.tools.modules import get_software_root, get_software_version


class EB_NWChem(ConfigureMake):
    """Support for building/installing NWChem."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for NWChem."""
        super(EB_NWChem, self).__init__(*args, **kwargs)

        self.example = None

    @staticmethod
    def extra_options():
        """Custom easyconfig parameters for NWChem."""

        extra_vars = [
                      ('target', ['LINUX64', "Target platform", CUSTOM]),
                      # possible options for ARMCI_NETWORK on LINUX64 with Infiniband:
                      # OPENIB, MPI-MT, MPI-SPAWN, MELLANOX
                      ('armci_network', ['OPENIB', "Network protocol to use", CUSTOM]),
                      ('modules', ["all", "NWChem modules to build", CUSTOM]),
                      ('lib_defines', ['', "Additional defines for C preprocessor", CUSTOM]),
                      ('with_nbo_support', [False, "Enable NBO support", CUSTOM]),
                     ]
        return ConfigureMake.extra_options(extra_vars)

    def configure_step(self):
        """Custom configuration procedure for NWChem."""

        # building NWChem in a long path name is an issue, so let's make sure we have a short one
        try:
            # NWChem insists that version is in name of build dir
            tmpdir = tempfile.mkdtemp(suffix=self.version)
            os.rmdir(tmpdir)
            os.symlink(self.cfg['start_dir'], tmpdir)
            os.chdir(tmpdir)
            self.cfg['start_dir'] = tmpdir
        except OSError, err:
            self.log.error("Failed to symlink build dir to a shorter path name: %s" % err)

        # change to actual build dir
        try:
            os.chdir('src')
        except OSError, err:
            self.log.error("Failed to change to build dir: %s" % err)

        nwchem_modules = self.cfg['modules']

        # set required NWChem environment variables
        env.setvar('NWCHEM_TOP', self.cfg['start_dir'])
        env.setvar('NWCHEM_TARGET', self.cfg['target'])
        env.setvar('ARMCI_NETWORK', self.cfg['armci_network'])

        if 'python' in self.cfg['modules']:
            python_root = get_software_root('Python')
            if not python_root:
                self.log.error("Python module not loaded, you should add Python as a dependency.")
            env.setvar('PYTHONHOME', python_root)
            env.setvar('PYTHONVERSION', '.'.join(get_software_version('Python').split('.')[0:2]))

        env.setvar('LARGE_FILES', 'TRUE')
        env.setvar('USE_NOFSCHECK', 'TRUE')
        env.setvar('LIB_DEFINES', self.cfg['lib_defines'])

        for var in ['USE_MPI', 'USE_MPIF', 'USE_MPIF4']:
            env.setvar(var, 'y')
        env.setvar('MPI_LOC', os.path.dirname(os.getenv('MPI_INC_DIR')))
        env.setvar('MPI_LIB', os.getenv('MPI_LIB_DIR'))
        env.setvar('MPI_INCLUDE', os.getenv('MPI_INC_DIR'))
        libmpi = None
        mpi_family = self.toolchain.mpi_family()
        if mpi_family in toolchain.OPENMPI:
            libmpi = "-lmpi_f90 -lmpi_f77 -lmpi -ldl -Wl,--export-dynamic -lnsl -lutil"
        elif mpi_family in [toolchain.INTELMPI]:
            libmpi = "-lmpi -lmpiif"
        elif mpi_family in [toolchain.MPICH2]:
            libmpi = "-lmpich -lopa -lmpl -lrt -lpthread"
        else:
            self.log.error("Don't know how to set LIBMPI for %s" % mpi_family)
        env.setvar('LIBMPI', libmpi)

        # BLAS and ScaLAPACK
        env.setvar('HAS_BLAS', 'yes')
        env.setvar('BLASOPT', '-L%s %s' % (os.getenv('BLAS_LIB_DIR'), os.getenv('LIBBLAS')))

        env.setvar('USE_SCALAPACK', 'y')
        env.setvar('SCALAPACK', '%s %s' % (os.getenv('LDFLAGS'), os.getenv('LIBSCALAPACK')))

        # enable NBO support if desired
        if self.cfg['with_nbo_support']:
            nwnbo_file = 'nwnbo.f'  # where should this come from?
            target = os.path.join(self.cfg['start_dir'], 'src', 'nbo')
            shutil.copyfile(nwnbo_file, target)
            nwchem_modules += ' nbo'

        env.setvar('NWCHEM_MODULES', nwchem_modules)
        self.log.info('NWCHEM_MODULES set to %s' % os.getenv('NWCHEM_MODULES'))

        # clean first (why not)
        run_cmd("make clean", simple=True, log_all=True, log_ok=True)

        # configure build
        run_cmd("make nwchem_config", simple=True, log_all=True, log_ok=True)

    def build_step(self):
        """Custom built-in test procedure for NWChem."""

        # set FC
        env.setvar('FC', os.getenv('F77'))
        self.log.info('FC set to %s' % os.getenv('FC'))

        # check whether 64-bit integers should be used, and act on it
        if not self.toolchain.options['i8']:
            par = ''
            if self.cfg['parallel']:
                par = '-j %s' % self.cfg['parallel']
            run_cmd("make %s 64_to_32" % par, simple=True, log_all=True, log_ok=True)

            env.setvar('USE_64TO32', "y")

        libs = os.getenv('LIBS')
        if libs:
            self.log.info("LIBS was defined as '%s', need to unset it to avoid problems..." % libs)
        os.unsetenv('LIBS')
        os.environ.pop('LIBS')

        super(EB_NWChem, self).build_step()

        # TODO: run getmem.nwchem script to assess memory availability and make an educated guess,
        # recompile the appropriate files and relink

    def test_step(self):
        """Custom built-in test procedure for NWChem."""

        if self.cfg['runtest']:
            cmd = "test command"
            run_cmd(cmd,  simple=True, log_all=True, log_ok=True)

    def install_step(self):
        """Custom install procedure for NWChem."""

        try:
            # binary
            bindir = os.path.join(self.installdir, 'bin')
            mkdir(bindir)
            shutil.copy(os.path.join(self.cfg['start_dir'], 'bin', self.cfg['target'], 'nwchem'),
                        bindir)

            # data
            datadir = os.path.join(self.installdir, 'data')
            mkdir(datadir)

            src_datadir = os.path.join(self.cfg['start_dir'], 'data')
            for path in os.listdir(src_datadir):
                fullpath = os.path.join(src_datadir, path)
                if os.path.isfile(fullpath):
                    shutil.copy2(fullpath, datadir)
                else:
                    shutil.copytree(fullpath, datadir)

            shutil.copytree(os.path.join(self.cfg['start_dir'], 'src', 'basis', 'libraries'), datadir)
            shutil.copytree(os.path.join(self.cfg['start_dir'], 'src', 'nwpw', 'libraryps'), datadir)

        except OSError, err:
            self.log.error("Failed to install NWChem: %s" % err)

    def sanity_check_step(self):
        """Custom sanity check for NWChem."""

        custom_paths = {
                        'files': ['bin/nwchem'],
                        'dirs': [os.path.join('data', x) for x in ['amber_q', 'amber_s', 'amber_t',
                                                                   'amber_u', 'amber_x', 'charmm_s',
                                                                   'charmm_x', 'solvents',
                                                                   'libraries', 'libraryps']],
                       }

        super(EB_NWChem, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Custom extra module file entries for NWChem."""

        txt = super(EB_NWChem, self).make_module_extra()

        txt += self.moduleGenerator().set_environment("PYTHONHOME", get_software_root('Python'))
        txt += self.moduleGenerator().prepend_paths("PYTHONPATH", ['path1', 'path2'])

        return txt
