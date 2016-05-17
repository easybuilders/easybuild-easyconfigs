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
EasyBuild support for building and installing SCons, implemented as an easyblock

@author: Balazs Hajgato (Free University Brussels (VUB))
"""

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.run import run_cmd

class SCons(EasyBlock):
    """Support for building/installing with SCons."""

    def configure_step(self):
        """
        No configure step for SCons
        """
        pass

    def build_step(self, verbose=False):
        """
        Build with SCons 
        """
        cmd = "%s scons %s PREFIX=%s" % (self.cfg['prebuildopts'], self.cfg['buildopts'], self.installdir)
        (out, _) = run_cmd(cmd, log_all=True, log_output=verbose)

        return out

    def test_step(self):
        """
        Test with SCons 
        """
        if self.cfg['runtest']:
            cmd = "scons %s" % (self.cfg['runtest'])
            run_cmd(cmd, log_all=True)

    def install_step(self):
        """
        Install with SCons
        """
        cmd = "%s scons PREFIX=%s install %s" % (self.cfg['preinstallopts'], self.installdir, self.cfg['installopts'])
        (out, _) = run_cmd(cmd, log_all=True)

        return out
