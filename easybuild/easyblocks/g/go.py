##
# Copyright 2014 Ghent University
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
EasyBuild support for building and installing Go, implemented as an easyblock

@author: Adam DeConinck (NVIDIA)
@author: Kenneth Hoste (HPC-UGent)
"""
import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.filetools import rmtree2, run_cmd

class EB_Go(ConfigureMake):
    """
    Build Go compiler
    """
    def configure_step(self):
        """No dedicated configure step."""
        pass

    def build_step(self):
        """No dedicated build step, building & installing is done in one go."""
        pass

    def install_step(self):
        """
        Execute the all.bash script to build and install the Go compiler,
        specifying the final installation prefix by setting $GOROOT_FINAL.
        """
        srcdir = os.path.join(self.cfg['start_dir'], 'src')
        try:
            os.chdir(srcdir)
        except OSError, err:
            self.log.error("Failed to move to %s: %s" % (srcdir, err))

        # $GOROOT_FINAL only specifies the location of the final installation, which gets baked into the binaries
        # the installation itself is *not* done by the all.bash script, that needs to be done manually
        cmd = "GOROOT_FINAL=%s ./all.bash" % self.installdir
        run_cmd(cmd, log_all=True, simple=False)

        try:
            rmtree2(self.installdir)
            shutil.copytree(self.cfg['start_dir'], self.installdir, symlinks=self.cfg['keepsymlinks'])
        except OSError, err:
            self.log.error("Failed to copy installation to %s: %s" % (self.installdir, err))
