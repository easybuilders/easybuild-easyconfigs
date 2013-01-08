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
EasyBuild support for building and installing the Bioconductor R library, implemented as an easyblock

@authors: Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Jens Timmerman, Toon Willems (Ghent University)
"""
from easybuild.easyblocks.generic.rpackage import RPackage


class EB_Rserve(RPackage):
    """Build and install Rserve R library."""

    def run(self):
        """Set LIBS environment variable correctly prior to building."""

        self.configurevars = ['LIBS="$LIBS -lpthread"']
        super(EB_Rserve, self).run()
