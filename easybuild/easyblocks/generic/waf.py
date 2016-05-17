##
# Copyright 2015-2016 Ghent University
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
EasyBuild support for software that uses the Waf build system.

@author: Kenneth Hoste (Ghent University)
"""

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.run import run_cmd


class Waf(EasyBlock):
    """
    Support for building and installing applications with waf
    """

    def configure_step(self, cmd_prefix=''):
        """
        Configure with ./waf configure --prefix=<installdir>
        """
        cmd = ' '.join([
            self.cfg['preconfigopts'],
            './waf',
            'configure',
            '--prefix=%s' % self.installdir,
            self.cfg['configopts'],
        ])
        (out, _) = run_cmd(cmd, log_all=True, simple=False)

        return out

    def build_step(self, verbose=False, path=None):
        """
        Build with ./waf build
        """
        cmd = ' '.join([
            self.cfg['prebuildopts'],
            './waf',
            'build',
            self.cfg['buildopts'],
        ])
        (out, _) = run_cmd(cmd, log_all=True, simple=False)

        return out

    def install_step(self, verbose=False, path=None):
        """
        Install with ./waf install
        """
        cmd = ' '.join([
            self.cfg['preinstallopts'],
            './waf',
            'install',
            self.cfg['installopts'],
        ])
        (out, _) = run_cmd(cmd, log_all=True, simple=False)

        return out
