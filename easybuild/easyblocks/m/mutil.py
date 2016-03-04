##
# Copyright 2016-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
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
import re
import os

from easybuild.easyblocks.generic.makecp import MakeCp
from easybuild.tools.build_log import EasyBuildError


class EB_mutil(MakeCp):
    """Class to build mutil"""

    def __init__(self, *args, **kwargs):
        """Easyblock constructor, set correct options"""
        super(EB_mutil, self).__init__(*args, **kwargs)

        self.cfg['with_configure'] = True

    def extract_step(self):
        """Set the start dir correctly and add patch from source."""
        super(EB_mutil, self).extract_step()

        # 1.822.3 -> 8.22
        coreutils_version = re.sub(r"^\d+.(\d+)(\d\d).\d+", r"\1.\2", self.version)
        coreutils_patch = "coreutils-%s.patch" % coreutils_version
        patch_path = os.path.join(self.builddir, "%s-%s" % (self.name, self.version), "patch", coreutils_patch)
        if not os.path.isfile(patch_path):
            raise EasyBuildError("Could not find the patch for coreutils: %s", coreutils_patch)

        # add the extract patch to the list of patches
        newpatch = {
            'name': coreutils_patch,
            'path': patch_path,
            'checksum': None,
        }
        self.patches.insert(0, newpatch)
