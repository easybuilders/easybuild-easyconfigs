##
# Copyright 2009-2016 Ghent University
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
EasyBuild support for installing QLogic MPI (RPM).

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Toon Willems (Ghent University)
"""

import os

from easybuild.easyblocks.generic.rpm import Rpm


class EB_QLogicMPI(Rpm):

    def make_module_extra(self):
        """Add MPICH_ROOT to module file."""
        
        txt = super(EB_QLogicMPI, self).make_module_extra()

        txt += self.module_generator.set_environment('MPICH_ROOT', self.installdir)

        return txt

    def sanity_check_step(self):
        """Custom sanity check for QLogicMPI."""

        custom_paths = {
                        'files': [os.path.join('bin', x) for x in ['mpirun', 'mpicc', 'mpicxx', 'mpif77', 'mpif90']] +
                                 [os.path.join('include', 'mpi.h')],
                        'dirs': [],
                       }

        super(EB_QLogicMPI, self).sanity_check_step(custom_paths=custom_paths)
