# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
# Author: Pablo Escobar Lopez
# Swiss Institute of Bioinformatics
# Biozentrum - University of Basel
"""
EasyBuild support for installing Chimera, implemented as an easyblock
"""

import os

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import run_cmd


class EB_Chimera(EasyBlock):
    """Support for installing Chimera."""
    
    def extract_step(self, verbose=False):
   
        # extract the installer .bin file . This will generate "chimera.bin" and "installer"
        # cmd is something like "unzip -d /tmp/easybuild/chimera/ /src/dir/chimera-1.0.bin
        cmd = "unzip -d %s %s" % (self.builddir, self.src[0]['path'])
        run_cmd(cmd, log_all=True, simple=True)
        
    def configure_step(self, cmd_prefix=''):
        """ skip configure """
        pass
    
    def build_step(self, verbose=False):
        """ skip build """
        pass
    
    def install_step(self):

        # command line to install
        cmdinstall = "cd %s; ./chimera.bin -q -d %s" % (self.cfg['start_dir'], self.installdir)

        # and now execute the installation
        run_cmd(cmdinstall, log_all=True, simple=True)
