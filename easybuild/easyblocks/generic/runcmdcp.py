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
# along with EasyBuild. If not, see <http://www.gnu.org/licenses/>.
##
"""
@author: Jens Timmerman (Ghent University)
"""
import os

from easybuild.easyblocks.generic.makecp import MakeCp
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import run_cmd


class RunCmdCp(MakeCp):
    """
    Software with no configure, no make, and no make install step.
    Just run a command with a glob pattern for all soruces and copy everything to the install dir
    """
    @staticmethod
    def extra_options(extra_vars=None):
        """
        Define list of files or directories to be copied after make
        """
        if not extra_vars:
            extra_vars = {}
        extra_vars['command'] = [
            '$CC -c $CFLAGS -o %(outputfile)s %(inputfile)s',
            'Compilation command, this will be templated with "inputfile" and "outputfile" for each matched file in the'
            'files_to_compile list"',
            CUSTOM,
        ]
        extra_vars['files_to_copy'] = [{}, "List of files or dirs to copy", CUSTOM]

        return extra_vars

    def build_step(self):
        """Build by running the command with the inputfiles"""
        try:
            os.chdir(self.cfg['start_dir'])
        except OSError, err:
            self.log.error("Failed to move (back) to %s: %s" % (self.cfg['start_dir'], err))

        command = self.cfg.get('command')
        outputfiles = []
        for fil in self.src:
            # run cmd on individual file
            fil = fil['path']
            out, _ = os.path.splitext(fil)
            cmd = command % {'inputfile': fil, 'outputfile': out}
            run_cmd(cmd, log_all=True, simple=True)
            outputfiles.append(out)
        self.cfg['files_to_copy'] = outputfiles
