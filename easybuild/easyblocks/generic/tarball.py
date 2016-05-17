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
EasyBuild support for installing (precompiled) software which is supplied as a tarball,
implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import shutil

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import rmtree2


class Tarball(EasyBlock):
    """
    Precompiled software supplied as a tarball:
    - will unpack binary and copy it to the install dir
    """

    def configure_step(self):
        """
        Dummy configure method
        """
        pass

    def build_step(self):
        """
        Dummy build method: nothing to build
        """
        pass

    def install_step(self, src=None):
        """Install by copying from specified source directory (or 'start_dir' if not specified)."""
        if src is None:
            src = self.cfg['start_dir']

        # shutil.copytree cannot handle destination dirs that exist already.
        # On the other hand, Python2.4 cannot create entire paths during copytree.
        # Therefore, only the final directory is deleted.
        rmtree2(self.installdir)
        try:
            # self.cfg['keepsymlinks'] is False by default except when explicitly put to True in .eb file
            shutil.copytree(src, self.installdir, symlinks=self.cfg['keepsymlinks'])
        except OSError, err:
            raise EasyBuildError("Copying %s to installation dir %s failed: %s", src, self.installdir, err)
