##
# Copyright 2009-2012 Stijn Deweirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
import os
import shutil
from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd_qa

class Maple(Application):
    """Support for installing Maple."""

    def unpack_src(self):
        """Unpacking of files is just copying Maple binary installer to build dir."""

        for f in self.src:
            shutil.copy(f['path'], os.path.join(self.builddir, f['name']))
            f['finalpath'] = self.builddir

    def configure(self):
        pass

    def make(self):
        pass

    def make_install(self):
        """Interactive install of Maple."""

        cmd="%s/Maple%sLinuxX86_64Installer.bin"%(self.builddir, self.getcfg('version'))

        qa={'PRESS <ENTER> TO CONTINUE:':'',
            'DO YOU ACCEPT THE TERMS OF THIS LICENSE AGREEMENT? (Y/N):':'Y',
            'ENTER AN ABSOLUTE PATH, OR PRESS <ENTER> TO ACCEPT THE DEFAULT :':self.installdir,
            'IS THIS CORRECT? (Y/N):':'Y',
            'Do you wish to have a shortcut installed on your desktop? ->1- Yes 2- No ENTER THE NUMBER FOR YOUR CHOICE, OR PRESS <ENTER> TO ACCEPT THE DEFAULT::':'2',
            '->1- Single User License 2- Network License ENTER THE NUMBER FOR YOUR CHOICE, OR PRESS <ENTER> TO ACCEPT THE DEFAULT::':'2',
            'PRESS <ENTER> TO EXIT THE INSTALLER:':'',
            'License server (DEFAULT: ):':self.getcfg('licenseServer'),
            'Port number (optional) (DEFAULT: ):':'',
            '->1- Configure toolbox for Matlab 2- Do not configure at this time ENTER THE NUMBER FOR YOUR CHOICE, OR PRESS <ENTER> TO ACCEPT THE DEFAULT::':'2'
            }

        no_qa=['Graphical installers are not supported by the VM. The console mode will be used instead...',
               'Extracting the JRE from the installer archive...',
               'Launching installer...',
               "Configuring the installer for this system's environment...",
               'Unpacking the JRE...',
               '\[[-|]*']

        run_cmd_qa(cmd,qa, no_qa=no_qa, log_all=True, simple=True)