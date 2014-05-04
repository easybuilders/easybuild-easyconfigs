##
# Copyright 2009-2013 Ghent University
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
"""
import os

from easybuild.easyblocks.generic.makecp import MakeCp
from easybuild.tools.filetools import run_cmd

class EB_Go(MakeCp):
    """
    Build Go compiler
    """

    def build_step(self, verbose=False):
        """
        Execute the all.bash script to build the Go compiler,
        setting GOROOT_FINAL to the eventual install location.
        """   
        try:
             os.chdir("%s/src" % (self.cfg['start_dir']))
        except OSError, err:
             self.log.error("Failed to move (back) to %s: %s" % (self.cfg['start_dir'], err))
        cmd = "GOROOT_FINAL=%s ./all.bash" % (self.installdir)
        (out, _) = run_cmd(cmd, log_all=True, simple=False, log_output=verbose)
        return out
