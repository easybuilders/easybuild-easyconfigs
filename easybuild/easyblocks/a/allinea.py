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
EasyBuild support for building and installing Allinea tools, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os
import shutil
from os.path import expanduser

from easybuild.easyblocks.generic.binary import Binary
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError


class EB_Allinea(Binary):
    """Support for building/installing Allinea."""

    @staticmethod
    def extra_options(extra_vars=None):
        """Define extra easyconfig parameters specific to Allinea."""
        extra = Binary.extra_options(extra_vars)
        extra.update({
            'templates': [[], "List of templates.", CUSTOM],
        })
        return extra

    def extract_step(self):
        """Extract Allinea installation files."""
        EasyBlock.extract_step(self)

    def configure_step(self):
        """No configuration for Allinea."""
        # ensure a license file is specified
        if self.cfg['license_file'] is None:
            raise EasyBuildError("No license file specified.")

    def build_step(self):
        """No build step for Allinea."""
        pass

    def install_step(self):
        """Install Allinea using install script."""

        if self.cfg['install_cmd'] is None:
            self.cfg['install_cmd'] = "./textinstall.sh --accept-licence %s" % self.installdir

        super(EB_Allinea, self).install_step()

        # copy license file
        lic_path = os.path.join(self.installdir, 'licences')
        try:
            shutil.copy2(self.cfg['license_file'], lic_path)
        except OSError, err:
            raise EasyBuildError("Failed to copy license file to %s: %s", lic_path, err)

        # copy templates
        templ_path = os.path.join(self.installdir, 'templates')
        for templ in self.cfg['templates']:
            try:
                shutil.copy2(templ, templ_path)
            except OSError, err:
                raise EasyBuildError("Failed to copy template %s to %s: %s", templ, templ_path, err)

    def sanity_check_step(self):
        """Custom sanity check for Allinea."""
        custom_paths = {
            'files': ['bin/ddt', 'bin/map'],
            'dirs': [],
        }
        super(EB_Allinea, self).sanity_check_step(custom_paths=custom_paths)
