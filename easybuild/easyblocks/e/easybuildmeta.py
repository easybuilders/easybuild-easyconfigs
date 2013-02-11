# #
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
# #
"""
EasyBuild support for installing EasyBuild, implemented as an easyblock

@author: Kenneth Hoste (UGent)
"""
import os

from easybuild.framework.easyblock import EasyBlock
from easybuild.easyblocks.generic.easy_install import Easy_install


# note: we can't use EB_EasyBuild as easyblock name, as that would require an easyblock named 'easybuild.py',
#       which would screw up namespacing and create all kinds of problems (e.g. easyblocks not being found anymore)
class EB_EasyBuildMeta(Easy_install):
    """Support for install EasyBuild."""

    def install_step(self):
        """Install Python package to a custom path using easy_install."""

        super(EB_EasyBuildMeta, self).install_step()

    def sanity_check_step(self):
        """Custom sanity check for EasyBuild."""

        custom_paths = {
                        'files': ['bin/eb'],
                        'dirs': [os.path.join(self.installdir, self.pylibdir)],
                       }

        custom_commands = [
                           ('eb', '--version'),
                           ('eb', '-a'),
                           ('eb', '-e ConfigureMake -a')
                          ]

        EasyBlock.sanity_check_step(self, custom_paths=custom_paths, custom_commands=custom_commands)
