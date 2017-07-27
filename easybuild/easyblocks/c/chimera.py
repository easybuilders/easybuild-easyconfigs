# This file is an EasyBuild reciPY as per https://github.com/easybuilders/easybuild
# Author: Pablo Escobar Lopez
# Swiss Institute of Bioinformatics
# Biozentrum - University of Basel
"""
EasyBuild support for installing Chimera, implemented as an easyblock
"""

import os

from easybuild.easyblocks.generic.packedbinary import PackedBinary
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class EB_Chimera(PackedBinary):
    """Support for installing Chimera."""

    def extract_step(self, verbose=False):
        """Custom extraction of sources for Chimera: unpack installation file
        to obtain chimera.bin installer."""

        cmd = "unzip -d %s %s" % (self.builddir, self.src[0]['path'])
        run_cmd(cmd, log_all=True, simple=True)

    def install_step(self):
        """Install using chimera.bin."""

        try:
            os.chdir(self.cfg['start_dir'])
        except OSError, err:
            raise EasyBuildError("Failed to change to %s: %s", self.cfg['start_dir'], err)

        cmd = "./chimera.bin -q -d %s" % self.installdir

        run_cmd(cmd, log_all=True, simple=True)
