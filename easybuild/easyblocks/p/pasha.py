##
# Copyright 2012 Jens Timmerman
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
pasha easyblock
"""
from easybuild.framework.application import Application

class Pasha(Application):
    """
    Extend Application to add extra configuration (overwrite variables in makefile)
    """

    def configure(self):
        """overwriting configure from Application
        Set some extra makeopts
        """
        makeopts = self.getcfg('makeopts')
        makeopts = "%s TBB_DIR=$SOFTROOTTBB/tbb MPI_CXX=$MPICXX OPM_FLAG=%s "\
                   "MPI_DIR='' MPI_INC='' MPI_LIB='' MY_CXX=$CXX " % (makeopts, self.tk.get_openmp_flag())

        self.setcfg('makeopts', makeopts)
