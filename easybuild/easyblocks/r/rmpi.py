##
# Copyright 2009-2013 Ghent University
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
EasyBuild support for building and installing the Rmpi R library, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Toon Willems (Ghent University)
"""
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.rpackage import RPackage


class EB_Rmpi(RPackage):
    """Build and install Rmpi R library."""

    def run(self):
        """Set various configure arguments prior to building."""

        mpi_types = {
            toolchain.MPI_TYPE_OPENMPI: "OPENMPI",
            toolchain.MPI_TYPE_MPICH: "MPICH",
            #toolchain.MPI_TYPE_LAM: "LAM",  # no support for LAM yet
        }

        self.log.debug("Setting configure args for Rmpi")
        self.configureargs = [
            "--with-Rmpi-include=%s" % self.toolchain.get_variable('MPI_INC_DIR'),
            "--with-Rmpi-libpath=%s" % self.toolchain.get_variable('MPI_LIB_DIR'),
            "--with-mpi=%s" % self.toolchain.get_software_root(self.toolchain.MPI_MODULE_NAME)[0],
            "--with-Rmpi-type=%s" % mpi_types[self.toolchain.MPI_TYPE],
        ]
        super(EB_Rmpi, self).run()  # it might be needed to get the R cmd and run it with mympirun...
