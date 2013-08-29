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
EasyBuild support for building and installing Mathematica, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os

from easybuild.easyblocks.generic.binary import Binary
from easybuild.tools.filetools import run_cmd_qa


class EB_Mathematica(Binary):
    """Support for building/installing Mathematica."""

    def configure_step(self):
        """No configuration for Mathematica."""
        pass

    def build_step(self):
        """No build step for Mathematica."""
        pass

    def install_step(self):
        """Install Mathematica using install script."""
        cmd = "./%s_%s_LINUX.sh" % (self.name, self.version)
        shortver = '.'.join(self.version.split('.')[:2])
        default_install_path = "/usr/local/Wolfram/%s/%s" % (self.name, shortver)
        qa = {
            "Enter the installation directory, or press ENTER to select %s: >" % default_install_path: self.installdir,
            "Create directory (y/n)? >": 'y',
            "or press ENTER to select /usr/local/bin: >": os.path.join(self.installdir, "bin"), 
        }
        no_qa = [
            "Now installing.*\n\n.*\[.*\].*",
        ]
        run_cmd_qa(cmd, qa, no_qa=no_qa, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for Mathematica."""
        custom_paths = {
            'files': ['bin/mathematica'],
            'dirs': ['AddOns', 'Configuration', 'Documentation', 'Executables', 'SystemFiles'],
        }
        super(EB_Mathematica, self).sanity_check_step(custom_paths=custom_paths)
