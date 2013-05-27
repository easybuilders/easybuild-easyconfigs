##
# Copyright 2013 The Cyprus Institute
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
EasyBuild support for GenomeAnalysisTK, implemented as an easyblock

@authors: George Tsouloupas (The Cyprus Institute)
@author: Fotis Georgatos (University of Luxembourg)
"""
import os
import shutil

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import run_cmd

class EB_GATK(EasyBlock):
    """Support for building and installing ant."""

    def configure_step(self):
        """No configure step for ant."""
        pass

    def build_step(self):
        """No build step for ant."""
        pass

    def install_step(self):
        """Custom install procedure for GenomeAnalysisTK.jar."""
        src = self.cfg['start_dir']
        shutil.copy2(os.path.join(src, 'GenomeAnalysisTK.jar'),self.installdir)
        shutil.copytree(os.path.join(src, 'resources'),os.path.join(self.installdir, 'resources'))

