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
EasyBuild support for building and installing FreeSurfer, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""

import os

from easybuild.easyblocks.generic.tarball import Tarball
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import MANDATORY
from easybuild.tools.build_log import EasyBuildError


class EB_FreeSurfer(Tarball):
    """Support for building and installing FreeSurfer."""

    @staticmethod
    def extra_options():
        extra_vars = {
            'license_text': ['', "Text for required license file.", MANDATORY],
        }
        return EasyBlock.extra_options(extra_vars)

    def install_step(self):
        """Custom installation procedure for FreeSurfer, which includes installed the license file '.license'."""
        txt = super(EB_FreeSurfer, self).install_step()
        try:
            f = open(os.path.join(self.installdir, '.license'), 'w')
            f.write(self.cfg['license_text'])
            f.close()
        except IOError, err:
            raise EasyBuildError("Failed to install license file: %s", err)

    def make_module_extra(self):
        """Add setting of FREESURFER_HOME in module."""
        txt = super(EB_FreeSurfer, self).make_module_extra()
        txt += self.module_generator.set_environment("FREESURFER_HOME", self.installdir)
        return txt

    def sanity_check_step(self):
        """Custom sanity check for FreeSurfer"""

        custom_paths =  {
            'files': ['FreeSurferEnv.sh', '.license'],
            'dirs': ['bin', 'lib', 'mni'],
        }

        super(EB_FreeSurfer, self).sanity_check_step(custom_paths=custom_paths)
