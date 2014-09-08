##
# Copyright 2014 Ghent University
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
#
# This work implements a part of the HPCBIOS project and is a component of the policy:
# http://hpcbios.readthedocs.org/en/latest/HPCBIOS_2012-94.html
##
"""
EasyBuild support for installing Modeller, implemented as an easyblock

@author: Pablo Escobar Lopez (SIB - University of Basel)
"""

import os

from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import run_cmd_qa


class EB_Modeller(EasyBlock):
    """Support for installing Modeller."""

    def configure_step(self):
        """ Skip configuration step """
        pass

    def build_step(self):
        """ Skip build step """
        pass

    def install_step(self):
        """Interactive install of Modeller."""

        cmd = "%s/Install" % (self.cfg'start_dir')

        # by default modeller tries to install to $HOME/bin/modeller9.13
        # get this path to use it in the question/answer
        default_install_path = "[%s]:" % os.path.join(os.path.expanduser('~'), 'bin', 'modeller%s' % self.cfg['version'])

        qa = {
             # installer will autodetect the right arch. [3] = x86_64
             'Select the type of your computer from the list above [3]:': '',
             default_install_path: self.installdir,
             'http://salilab.org/modeller/registration.html:': self.cfg["license_key"],
             'Press <Enter> to begin the installation:': '',
             'Press <Enter> to continue:': ''
             }

        run_cmd_qa(cmd, qa, log_all=True, simple=True)
