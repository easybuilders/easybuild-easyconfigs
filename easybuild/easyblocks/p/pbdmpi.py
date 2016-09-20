##
# Copyright 2015-2016 Ghent University
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
EasyBuild support for building and installing pbdMPI, implemented as an easyblock

@author: Ewan Higgs (Ghent University)
@author: Peter Maxwell (University of Auckland)
"""

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.rpackage import RPackage

class EB_pbdMPI(RPackage):
    """Support for building/installing pbdMPI."""

    def configure_step(self):
        """Configure Step of build process for pbdMPI."""
        mpi_types = {
            toolchain.INTELMPI: 'INTELMPI',
            toolchain.MPI_TYPE_MPICH: 'MPICH',
            toolchain.MPI_TYPE_OPENMPI: 'OPENMPI',
        }
        mpi_type = mpi_types[self.toolchain.mpi_family()]
        self.configureargs.extend([
            "--with-mpi-include=%s" % self.toolchain.get_variable('MPI_INC_DIR'),
            "--with-mpi-libpath=%s" % self.toolchain.get_variable('MPI_LIB_DIR'),
            "--with-mpi=%s" % self.toolchain.get_software_root(self.toolchain.MPI_MODULE_NAME)[0],
            "--with-mpi-type=%s" % mpi_type,
        ])

        super(EB_pbdMPI, self).configure_step()

    def run(self):
        """Configure before installing pbdMPI as an extension."""
        self.configure_step()
        super(EB_pbdMPI, self).run()
