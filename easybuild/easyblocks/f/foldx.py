##
# Copyright 2013 Ghent University
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
EasyBuild support for installing FoldX, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os
import shutil
import stat

from easybuild.easyblocks.generic.tarball import Tarball
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import adjust_permissions


class EB_FoldX(Tarball):
    """
    Support for installing FoldX
    """

    def install_step(self):
        """Install by copying files to install dir and binary to 'bin' install subdir, and fixing permissions."""

        bindir = os.path.join(self.installdir, 'bin')
        binaries = [
            'foldx_%s.linux' % self.version,  # FoldX v2.x
            'FoldX.linux64',  # FoldX 3.x
            'foldx64Linux',  # FoldX 3.0-beta6
            'foldx3b6',  # FoldX 3.0 beta 6.1 >_<
        ]
        try:
            os.makedirs(bindir)
            for item in os.listdir(self.cfg['start_dir']):
                if os.path.isfile(item):
                    if item in binaries:
                        shutil.copy2(os.path.join(self.cfg['start_dir'], item), bindir)
                        # make sure binary has executable permissions
                        adjust_permissions(os.path.join(bindir, item), stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH, add=True)
                        self.log.debug("Copied %s to %s and fixed permissions" % (item, bindir))
                    else:
                        # copy everything else straight into install directory
                        shutil.copy2(os.path.join(self.cfg['start_dir'], item), self.installdir)
                        self.log.debug("Copied %s to install dir %s" % (item, self.installdir))
                else:
                    self.log.warning("Skipping non-file %s in %s, not copying it." % (item, self.cfg['start_dir']))
        except OSError, err:
            raise EasyBuildError("Copying binaries in %s to install dir 'bin' failed: %s", self.cfg['start_dir'], err)

