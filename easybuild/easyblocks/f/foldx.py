##
# Copyright 2013 Ghent University
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""
EasyBuild support for installing FoldX, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os
import shutil
import stat

from easybuild.easyblocks.generic.tarball import Tarball
from easybuild.tools.filetools import adjust_permissions


class EB_FoldX(Tarball):
    """
    Support for installing FoldX
    """

    def install_step(self):
        """Install FoldX by copying unzipped binary to 'bin' subdir of installation dir, and fixing permissions."""

        binfile_name = '%s_%s.linux' % (self.name.lower(), self.version)
        binfile = os.path.join(self.cfg['start_dir'], binfile_name)
        bindir = os.path.join(self.installdir, 'bin')
        try:
            os.makedirs(bindir)
            shutil.copy2(binfile, bindir)
        except OSError, err:
            self.log.exception("Copying %s to installation dir failed: %s" % (binfile, err))

        # make sure binary has executable permissions
        adjust_permissions(os.path.join(bindir, binfile_name), stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH, add=True)

    def sanity_check_step(self):
        """Custom sanity check for FoldX."""
        custom_paths = {
            'files': ['bin/%s_%s.linux' % (self.name.lower(), self.version)],
            'dirs': [],
        }
        super(EB_FoldX, self).sanity_check_step(custom_paths=custom_paths)
