##
# Copyright 2009-2012 Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild. If not, see <http://www.gnu.org/licenses/>.
##
"""
EasyBlock for binary applications that need unpacking,
e.g., binary applications shipped as a .tar.gz file
"""

from easybuild.framework.application import Application
from easybuild.easyblocks.b.binary import Binary


class EB_PackedBinary(Binary, Application):
    """Support for installing a packed binary package.
    Just unpack its source in the installdir
    """

    def unpack_src(self):
        """Unpack the source"""
        Application.unpack_src(self)

