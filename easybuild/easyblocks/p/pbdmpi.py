##
# Copyright 2009-2015 Ghent University
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
EasyBuild support for building and installing pbdMPI, implemented as an easyblock
"""
import os

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.rpackage import RPackage
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
import easybuild.tools.toolchain as toolchain
from easybuild.tools.run import run_cmd


class EB_pbdMPI(RPackage):
    """Support for building/installing pbdMPI."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for pbdMPI."""
        super(EB_pbdMPI, self).__init__(*args, **kwargs)
        self.example = None

    def configure_step(self):
        mpi_types = {
                toolchain.INTELMPI: 'INTELMPI',
                toolchain.MPI_TYPE_MPICH: 'MPICH',
                toolchain.MPI_TYPE_OPENMPI: 'OPENMPI',
        }
        mpi_type = mpi_types[self.toolchain.mpi_family()]
        self.configureargs.append("--with-mpi-type=%s" % mpi_type)

        super(EB_pbdMPI, self).configure_step()


