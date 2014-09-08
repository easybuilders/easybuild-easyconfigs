# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
# Author: Pablo Escobar Lopez
# Swiss Institute of Bioinformatics
# Biozentrum - University of Basel
"""
EasyBuild support for installing Modeller, implemented as an easyblock
"""

import os

from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import run_cmd_qa


class EB_Modeller(EasyBlock):
    """Support for installing Modeller."""
    
    @staticmethod
    def extra_options():
        """Add extra easyconfig parameters custom to Modeller"""
        extra_vars = {
            'LICENSEKEY': ["", "Specify the modeller license key", CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

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
        default_install_path = '%s/bin/modeller%s' % (os.getenv('HOME'), self.cfg['version'])
        # add [ to beginning and ]: to end
        default_install_path = ''.join(('[',default_install_path,']:'))

        qa = {
             # installer will autodetect the right arch. [3] = x86_64
             'Select the type of your computer from the list above [3]:': '',
             default_install_path: self.installdir,
             'http://salilab.org/modeller/registration.html:': self.cfg["LICENSEKEY"],
             'Press <Enter> to begin the installation:': '',
             'Press <Enter> to continue:': ''
             }

        run_cmd_qa(cmd, qa, log_all=True, simple=True)
