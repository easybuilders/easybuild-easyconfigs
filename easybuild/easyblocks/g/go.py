##
# Copyright 2014 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/easybuilders/easybuild
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

from distutils.version import LooseVersion

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import rmtree2
from easybuild.tools.run import run_cmd
from easybuild.tools.modules import get_software_root

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
            raise EasyBuildError("Failed to move to %s: %s", srcdir, err)

        # $GOROOT_FINAL only specifies the location of the final installation, which gets baked into the binaries
        # the installation itself is *not* done by the all.bash script, that needs to be done manually
        # $GOROOT_BOOTSTRAP needs to specify a Go installation directory to build the go toolchain for versions
        # 1.5 and later.
        if LooseVersion(self.version) >= LooseVersion('1.5'):
            go_root = get_software_root('Go')
            if go_root:
                cmd = "GOROOT_BOOTSTRAP=%s GOROOT_FINAL=%s ./all.bash" % (go_root, self.installdir)
            else:
                raise EasyBuildError("Go is required as a build dependency for installing Go since version 1.5")
        else:
            cmd = "GOROOT_FINAL=%s ./all.bash" % self.installdir

        run_cmd(cmd, log_all=True, simple=False)

        try:
            rmtree2(self.installdir)
            shutil.copytree(self.cfg['start_dir'], self.installdir, symlinks=self.cfg['keepsymlinks'])
        except OSError, err:
            raise EasyBuildError("Failed to copy installation to %s: %s", self.installdir, err)
