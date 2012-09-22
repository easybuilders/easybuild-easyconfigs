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
from easybuild.easyblocks.binary import EB_Binary


class EB_PackedBinary(EB_Binary):
    """Support for installing a packed binary package.
    Just copy unpacked sources in the installdir
    """

    def make_install(self):
        """Unpack and copy all sources to install directory, one-by-one."""
        for src in self.src:
            # unpack, and try to determine resulting directory
            srcdir = unpack(src['path'], self.builddir, extra_options=self.getcfg('unpackOptions'))
            # copy files to install dir via EB_Binary
            self.setcfg('startfrom', srcdir)
            EB_Binary.make_install(self)
            # remove unpacked directory
            try:
                shutil.rmtree(os.path.join(self.builddir, srcdir))
            except OSError, err:
                self.log.error("Failed to remove %s: %s" % (srcdir, err))

