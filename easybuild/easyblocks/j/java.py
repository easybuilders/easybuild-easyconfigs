##
# Copyright 2012 Ghent University
# Copyright 2012 Jens Timmerman
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
from easybuild.easyblocks.generic.packedbinary import PackedBinary


class EB_Java(PackedBinary):
    """Support for installing java as a packed binary file (.tar.gz)
    Use the PackedBinary and set some extra paths.
    """
    def make_module_extra(self):
        """
        Set JAVA_HOME to install dir
        """
        txt = PackedBinary.make_module_extra(self)
        txt += self.moduleGenerator.set_environment('JAVA_HOME', '$root')
        return txt
