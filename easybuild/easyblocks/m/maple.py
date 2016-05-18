##
# Copyright 2009-2016 Ghent University
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
EasyBuild support for installing Maple, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os
import shutil

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.run import run_cmd_qa


class EB_Maple(EasyBlock):
    """Support for installing Maple."""

    def extract_step(self):
        """Unpacking of files is just copying Maple binary installer to build dir."""

        for f in self.src:
            shutil.copy(f['path'], os.path.join(self.builddir, f['name']))
            f['finalpath'] = self.builddir

    def configure_step(self):
        """No configuration needed, binary installer"""
        pass

    def build_step(self):
        """No compilation needed, binary installer"""
        pass

    def install_step(self):
        """Interactive install of Maple."""

        cmd = "%s/Maple%sLinuxX86_64Installer.bin" % (self.builddir, self.cfg['version'])

        qa = {
              'PRESS <ENTER> TO CONTINUE:': '',
              'DO YOU ACCEPT THE TERMS OF THIS LICENSE AGREEMENT? (Y/N):': 'Y',
              'ENTER AN ABSOLUTE PATH, OR PRESS <ENTER> TO ACCEPT THE DEFAULT :': self.installdir,
              'IS THIS CORRECT? (Y/N):': 'Y',
              'Do you wish to have a shortcut installed on your desktop? ->1- Yes 2- No ENTER THE NUMBER FOR YOUR CHOICE, OR PRESS <ENTER> TO ACCEPT THE DEFAULT::': '2',
              '->1- Single User License 2- Network License ENTER THE NUMBER FOR YOUR CHOICE, OR PRESS <ENTER> TO ACCEPT THE DEFAULT::': '2',
              'PRESS <ENTER> TO EXIT THE INSTALLER:': '',
              'License server (DEFAULT: ):': self.cfg['license_server'],
              'Port number (optional) (DEFAULT: ):': '',
              '->1- Configure toolbox for Matlab 2- Do not configure at this time ENTER THE NUMBER FOR YOUR CHOICE, OR PRESS <ENTER> TO ACCEPT THE DEFAULT::': '2'
             }

        no_qa = ['Graphical installers are not supported by the VM. The console mode will be used instead...',
                 'Extracting the JRE from the installer archive...',
                 'Launching installer...',
                 "Configuring the installer for this system's environment...",
                 'Unpacking the JRE...',
                 '\[[-|]*']

        run_cmd_qa(cmd, qa, no_qa=no_qa, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for Maple."""

        custom_paths =  {
                         'files': ['bin/maple', 'lib/maple.mla'] ,
                         'dirs':[]
                        }

        super(EB_Maple, self).sanity_check_step(custom_paths=custom_paths)
