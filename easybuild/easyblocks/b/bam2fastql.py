##
# Copyright 2013 The Cyprus Institute
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
@author: George Tsouloupas (The Cyprus Institute)
"""
import shutil
import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
from easybuild.tools.filetools import run_cmd

class EB_bam2fastq(ConfigureMake):
    """
    Software with no configure and no make install step.
    """
    @staticmethod
    def extra_options():
        """
        Define list of files or directories to be copied after make
        """
        extra_vars = [
                      ('files_to_copy', [{}, "List of files or dirs to copy", MANDATORY]),
                     ]
        return ConfigureMake.extra_options(extra_vars)

    def configure_step(self):
        """
        Dummy configure method
        """
        pass

#    def build_step(self, verbose=False):
#        cmd = "cd src && %s make %s" % (self.cfg['premakeopts'], self.cfg['makeopts'])
#
#        (out, _) = run_cmd(cmd, log_all=True, simple=False, log_output=verbose)
#
#        return out

    def install_step(self):

        src = self.cfg['start_dir']
        try:
            (out, _) = run_cmd("mkdir %s" % os.path.join(self.installdir,'bin'))
            for f in self.cfg["files_to_copy"]:
		print os.path.join(src,f)
                shutil.copy2(os.path.join(src,'src',f),os.path.join(self.installdir,'bin'))
        except:
            self.log.exception("Copying %s to installation dir %s failed" % (src,self.installdir))
