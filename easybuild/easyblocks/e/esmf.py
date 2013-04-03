##
# Copyright 2013 Ghent University
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
EasyBuild support for building and installing ESMF, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import BUILD
from easybuild.tools.filetools import run_cmd


class EB_ESMF(ConfigureMake):
    """Support for building/installing ESMF."""

    def __init__(self, *args, **kwargs):
        """Add extra config options specific to ESMF."""
        super(EB_ESMF, self).__init__(*args, **kwargs)

        self.subdir = None

    def configure_step(self):
        """Custom configuration procedure for ESMF through environment variables."""

        env.setvar('ESMF_DIR', self.cfg['start_dir'])
        env.setvar('ESMF_INSTALL_PREFIX', self.installdir)

        # specify compiler
        comp_family = self.toolchain.comp_family()
        if comp_family in [toolchain.GCC]:
            compiler = 'gfortran'
        else:
            compiler = comp_family.lower()
        env.setvar('ESMF_COMPILER', compiler)

        # specify MPI communications library
        comm = None
        mpi_family = self.toolchain.mpi_family()
        if mpi_family in [toolchain.QLOGICMPI]:
            comm = 'mpich'
        else:
            comm = mpi_family.lower()
        env.setvar('ESMF_COMM', comm)

        self.subdir = '.'.join(['Linux', compiler, '64', comm, 'default'])

        # 'make info' provides useful debug info
        cmd = "make info"
        run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def sanity_check_step(self):
        """Custom sanity check for ESMF."""

        custom_paths = {
            'files':
                [os.path.join('bin', 'bin0', self.subdir, x) for x in ['ESMF_Info', 'ESMF_InfoC', 'ESMF_RegridWeightGen', 'ESMF_WebServController']] +
                [os.path.join('lib', 'lib0', self.subdir, x) for x in ['libesmf.a', 'libesmf.so', 'libesmf_fullylinked.so']],
            'dirs': ['include', os.path.join('mod', 'mod0', self.subdir)],
        }

        super(EB_ESMF, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Custom guesses for environment variables (PATH, ...) for ESMF."""

        guesses = super(EB_ESMF, self).make_module_req_guess()

        guesses.update({
                        'PATH': [os.path.join('bin', 'bin0', self.subdir)],
                        'LD_LIBRARY_PATH': [os.path.join('lib', 'lib0', self.subdir)],
                       })

        return guesses
