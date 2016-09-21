# -*- coding: utf-8 -*-
##
# Copyright 2009-2016 Ghent University
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
EasyBuild support for installing Gurobi, implemented as an easyblock

@author: Bob Dröge (University of Groningen)
"""

import os
import shutil

from easybuild.easyblocks.generic.tarball import Tarball
from easybuild.tools.build_log import EasyBuildError


class EB_Gurobi(Tarball):
    """Support for installing linux64 version of Gurobi."""

    def configure_step(self):
        """No configuration for Gurobi."""
        # ensure a license file is specified
        if self.cfg['license_file'] is None or not os.path.exists(self.cfg['license_file']):
            raise EasyBuildError("No existing license file specified: %s", self.cfg['license_file'])

    def install_step(self):
        """Install Gurobi and license file."""

        super(EB_Gurobi, self).install_step()

        # copy license file
        lic_path = os.path.join(self.installdir, 'gurobi.lic')
        try:
            shutil.copy2(self.cfg['license_file'], lic_path)
        except OSError as err:
            raise EasyBuildError("Failed to copy license file to %s: %s", lic_path, err)

    def sanity_check_step(self):
        """Custom sanity check for Gurobi."""
        custom_paths = {
            'files': ['bin/%s' % f for f in ['grbprobe', 'grbtune', 'gurobi_cl', 'gurobi.sh']],
            'dirs': [],
        }
        super(EB_Gurobi, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Custom extra module file entries for Gurobi."""
        txt = super(EB_Gurobi, self).make_module_extra()

        txt += self.module_generator.set_environment('GUROBI_HOME', self.installdir)
        txt += self.module_generator.set_environment('GRB_LICENSE_FILE', os.path.join(self.installdir, 'gurobi.lic'))

        return txt

