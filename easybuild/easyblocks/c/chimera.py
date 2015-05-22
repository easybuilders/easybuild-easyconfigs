# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
# Author: Pablo Escobar Lopez
# Swiss Institute of Bioinformatics
# Biozentrum - University of Basel
"""
EasyBuild support for installing Chimera, implemented as an easyblock
"""

import os

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class EB_Chimera(EasyBlock):
    """Support for installing Chimera."""
    
    def extract_step(self, verbose=False):
        """Custom extraction of sources for Chimera: unpack installation file
        to obtain chimera.bin installer."""
   
        cmd = "unzip -d %s %s" % (self.builddir, self.src[0]['path'])
        run_cmd(cmd, log_all=True, simple=True)
        
    def configure_step(self, cmd_prefix=''):
        """ skip configure """
        pass
    
    def build_step(self, verbose=False):
        """ skip build """
        pass
    
    def install_step(self):
        """Install using chimera.bin."""

        try:
            os.chdir(self.cfg['start_dir'])
        except OSError, err:
            raise EasyBuildError("Failed to change to %s: %s", self.cfg['start_dir'], err)

        cmd = "./chimera.bin -q -d %s" % self.installdir

        run_cmd(cmd, log_all=True, simple=True)
