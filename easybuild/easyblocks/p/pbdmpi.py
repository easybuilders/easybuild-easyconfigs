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
EasyBuild support for building and installing the pbdMPI R library, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Toon Willems (Ghent University)
@author: Balazs Hajgato (Vrije Universiteit Brussel)
"""
import easybuild.tools.toolchain as toolchain
from distutils.version import LooseVersion
from easybuild.easyblocks.generic.rpackage import RPackage

# This is just a copy of EB_Rmpi with "--with-Rmpi-" changed to "--with-mpi-" and then simplified.

class EB_pbdMPI(RPackage):
    """Build and install pbdMPI R library."""

    def run(self):
        """Set various configure arguments prior to building."""
        
        mpi_types = {
            toolchain.MPI_TYPE_OPENMPI: "OPENMPI",
            toolchain.MPI_TYPE_MPICH: "MPICH",            
            #toolchain.MPI_TYPE_LAM: "LAM",  # no support for LAM yet
        }
        # MPI_TYPE does not distinguish between MPICH and IntelMPI, which is why we also check mpi_family()
        mpi_type = mpi_types[self.toolchain.MPI_TYPE]
        if self.toolchain.mpi_family() == toolchain.INTELMPI:
             mpi_type = 'INTELMPI'
        
        self.log.debug("Setting configure args for pbdMPI")
        self.configureargs = [
            "--with-mpi-include=%s" % self.toolchain.get_variable('MPI_INC_DIR'),
            "--with-mpi-libpath=%s" % self.toolchain.get_variable('MPI_LIB_DIR'),
            "--with-mpi=%s" % self.toolchain.get_software_root(self.toolchain.MPI_MODULE_NAME)[0],
            "--with-mpi-type=%s" % mpi_type,
        ]
        super(EB_pbdMPI, self).run()  # it might be needed to get the R cmd and run it with mympirun...

