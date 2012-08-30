##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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
EasyBuild support for Python packages that are configured with CMake, implemented as an easyblock
"""
from easybuild.easyblocks.cmake import EB_CMake
from easybuild.easyblocks.pythonpackage import EB_PythonPackage


class EB_CMakePythonPackage(EB_CMake, EB_PythonPackage):
    """Build a Python package and module with cmake.

    Some packages use cmake to first build and install C Python packages
    and then put the Python package in lib/pythonX.Y/site-packages.

    We install this in a seperate location and generate a module file 
    which sets the PYTHONPATH.

    We use the default CMake implementation, and use make_module_extra from PythonPackage.
    """

    def __init__(self, *args, **kwargs):
        """Initialize with PythonPackage."""
        EB_PythonPackage.__init__(self, *args, **kwargs)

    def configure(self, *args, **kwargs):
        """Main configuration using cmake"""

        EB_PythonPackage.configure(self, *args, **kwargs)

        return EB_CMake.configure(self, *args, **kwargs)

    def make(self, *args, **kwargs):
        """Build Python package with cmake"""
        return EB_CMake.make(self, *args, **kwargs)

    def make_install(self):
        """Install with cmake install"""
        return EB_CMake.make_install(self)

    def make_module_extra(self):
        """Add extra Python package module parameters"""
        return EB_PythonPackage.make_module_extra(self)
