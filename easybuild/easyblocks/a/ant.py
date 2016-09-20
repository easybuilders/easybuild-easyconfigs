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
EasyBuild support for ant, implemented as an easyblock

@authors: Stijn De Weirdt (UGent), Dries Verdegem (UGent), Kenneth Hoste (UGent), Pieter De Baets (UGent),
          Jens Timmerman (UGent)
"""
import os
import shutil

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd


class EB_ant(EasyBlock):
    """Support for building and installing ant."""

    def configure_step(self):
        """No configure step for ant."""
        pass

    def build_step(self):
        """No build step for ant."""
        pass

    def install_step(self):
        """Custom install procedure for ant."""

        junit_root = get_software_root('JUnit')
        if not junit_root:
            raise EasyBuildError("JUnit module not loaded!")

        junit_ver = get_software_version('JUnit')

        # copy JUnit jar to where it's expected
        try:
            shutil.copy(os.path.join(junit_root, 'junit-%s.jar' % junit_ver),
                        os.path.join(os.getcwd(), "lib", "optional"))
        except OSError, err:
            raise EasyBuildError("Failed to copy JUnit jar: %s", err)

        cmd = "sh build.sh -Ddist.dir=%s dist" % self.installdir

        run_cmd(cmd, log_all=True, simple=True)
