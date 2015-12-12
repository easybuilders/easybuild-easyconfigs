##
# Copyright 2009-2015 Ghent University
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
EasyBuild support for building and installing MRtrix, implemented as an easyblock
"""
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.run import run_cmd


class EB_MRtrix(EasyBlock):
    """Support for building/installing MRtrix."""

    def configure_step(self):
        """No configuration step for MRtrix."""
        pass

    def build_step(self):
        """Custom build procedure for MRtrix."""
        cmd = "./build"
        run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def install_step(self):
        """Custom install procedure for MRtrix."""
        cmd = "./build install=%s linkto=" % self.installdir
        run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def sanity_check_step(self):
        """Custom sanity check for MRtrix."""
        custom_paths = {
            'files': ['lib/libmrtrix-0_2_12.so'],
            'dirs': ['bin'],
        }
        super(EB_MRtrix, self).sanity_check_step(custom_paths=custom_paths)
