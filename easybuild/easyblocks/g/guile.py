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
EasyBuild support for building and installing guile, implemented as an easyblock
"""

from easybuild.easyblocks.generic.configuremake import ConfigureMake

class EB_guile(ConfigureMake):
    """
    Support for building/installing guile: default build procedure, and set correct CPATH.
    """

    def make_module_req_guess(self):
        """Add guile/2.0 to cpath"""

        guess = super(EB_guile, self).make_module_req_guess()
        guess['CPATH'] = guess['CPATH'] + ["include/guile/2.0"]

        return guess
