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
# along with EasyBuild. If not, see <http://www.gnu.org/licenses/>.
##
"""
@author: Jens Timmerman (Ghent University)
@author: Kenneth Hoste (Ghent Univeristy)
"""
import os
import re

from easybuild.easyblocks.generic.makecp import MakeCp
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class CmdCp(MakeCp):
    """
    Software with no configure, no make, and no make install step.
    Just run the specified command for all sources, and copy specified files to the install dir
    """
    @staticmethod
    def extra_options(extra_vars=None):
        """
        Define list of files or directories to be copied after make
        """
        extra_vars = MakeCp.extra_options(extra_vars=extra_vars)
        extra_vars['cmds_map'] = [
            [('.*', "$CC $CFLAGS %(source)s -o %(target)s")],
            "List of regex/template command (with 'source'/'target' fields) tuples",
            CUSTOM,
        ]
        return extra_vars

    def build_step(self):
        """Build by running the command with the inputfiles"""
        try:
            os.chdir(self.cfg['start_dir'])
        except OSError, err:
            raise EasyBuildError("Failed to move (back) to %s: %s", self.cfg['start_dir'], err)

        for src in self.src:
            src = src['path']
            target, _ = os.path.splitext(os.path.basename(src))

            # determine command to use
            # find (first) regex match, then complete matching command template
            cmd = None
            for regex, regex_cmd in self.cfg['cmds_map']:
                if re.match(regex, os.path.basename(src)):
                    cmd = regex_cmd % {'source': src, 'target': target}
                    break
            if cmd is None:
                raise EasyBuildError("No match for %s in %s, don't know which command to use.",
                                     src, self.cfg['cmds_map'])

            run_cmd(cmd, log_all=True, simple=True)
