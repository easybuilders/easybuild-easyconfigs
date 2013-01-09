##
# Copyright 2009-2013 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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

@authors: Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Jens Timmerman, Toon Willems (Ghent University)
"""
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.rpackage import RPackage


class EB_Rmpi(RPackage):
    """Build and install Rmpi R library."""

    MPI_TYPES = {
        toolchain.MPI_TYPE_OPENMPI: "OPENMPI",
        toolchain.MPI_TYPE_MPICH: "MPICH",
        #toolchain.MPI_TYPE_LAM: "LAM",  # no support for LAM yet
    }

    def run(self):
        """Set various configure arguments prior to building."""

        self.log.debug("Setting configure args for Rmpi")
        self.configureargs = [
            "--with-Rmpi-include=%s" % self.toolchain.get_variable('MPI_INC_DIR'),
            "--with-Rmpi-libpath=%s" % self.toolchain.get_variable('MPI_LIB_DIR'),
            "--with-mpi=%s" % self.toolchain.get_software_root(self.toolchain.MPI_MODULE_NAME)[0],
            "--with-Rmpi-type=%s" % EB_Rmpi.MPI_TYPES[self.toolchain.MPI_TYPE],
        ]
        super(EB_Rmpi, self).run()  # it might be needed to get the R cmd and run it with mympirun...
