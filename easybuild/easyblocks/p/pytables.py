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
"""Easyblock for PyTables"""

import os
from easybuild.easyblocks.p.pythonpackagemodule import PythonPackageModule
class PyTables(PythonPackageModule):
    """install the pytables package"""
    def __init__(self,*args,**kwargs):
         PythonPackageModule.__init__(self, *args,**kwargs)
         #pytables needs to know where HDF5 is
         #os.environ['HDF5'] = os.environ['SOFTROOTHDF5']

