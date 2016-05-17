##
# Copyright 2016-2016 Ghent University
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
EasyBuild support for mutil, implemented as an easyblock

@author: Ward Poelmans (Ghent University)
"""
import glob
import os
import re

from easybuild.easyblocks.generic.makecp import MakeCp
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import apply_patch


class EB_mutil(MakeCp):
    """Easyblock to build and install mutil"""

    @staticmethod
    def extra_options():
        """Change default values of options"""
        extra = MakeCp.extra_options()
        # files_to_copy is not mandatory here
        extra['files_to_copy'][2] = CUSTOM
        extra['with_configure'][0] = True
        return extra

    def configure_step(self):
        """Apply coreutils patch from source and run configure"""
        # 1.822.3 -> 8.22
        coreutils_version = re.sub(r"^\d+.(\d+)(\d\d).\d+", r"\1.\2", self.version)
        coreutils_patch = "coreutils-%s.patch" % coreutils_version
        patch_path = os.path.join(self.builddir, "%s-%s" % (self.name, self.version), "patch", coreutils_patch)
        if os.path.isfile(patch_path):
            self.log.info("coreutils patch found at %s", patch_path)
        else:
            raise EasyBuildError("Could not find the patch for coreutils: %s", coreutils_patch)

        coreutils_path = glob.glob(os.path.join(self.builddir, "coreutils-*"))
        if not coreutils_path:
            raise EasyBuildError("Could not find the coreutils directory")

        if not apply_patch(patch_path, coreutils_path[0]):
            raise EasyBuildError("Applying coreutils patch %s failed", coreutils_patch)

        super(EB_mutil, self).configure_step()

    def install_step(self):
        """Specify list of files to copy"""
        self.cfg['files_to_copy'] = [
            ([('src/cp', 'mcp'), ('src/md5sum', 'msum')], 'bin'),
            ([('man/cp.1', 'mcp.1'), ('man/md5sum.1', 'msum.1')], 'man/man1'),
        ]
        super(EB_mutil, self).install_step()
