##
# Copyright 2013 the Cyprus Institute
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
@author: Fotis Georgatos (University of Luxembourg)
@author: Kenneth Hoste (Ghent University)
"""
import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import BUILD, MANDATORY

class MakeCp(ConfigureMake):
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
            ('with_configure', [False, "Run configure script before building", BUILD]),
        ]
        return ConfigureMake.extra_options(extra_vars)

    def configure_step(self, cmd_prefix=''):
        """
        Configure build if required
        """
        if self.cfg.get('with_configure', False):
            return super(MakeCp, self).configure_step(cmd_prefix=cmd_prefix)

    def install_step(self):
        """Install by copying specified files and directories."""
        try:
            for fil in self.cfg.get('files_to_copy', {}):
                if isinstance(fil, tuple):
                    # ([src1, src2], targetdir)
                    if len(fil) == 2 and isinstance(fil[0], list) and isinstance(fil[1], basestring):
                        srcs = fil[0]
                        target = os.path.join(self.installdir, fil[1])
                    else:
                        self.log.error("Only tuples of format '([<source files>], <target dir>)' supported.")
                # 'src_file' or 'src_dir'
                elif isinstance(fil, basestring):
                    srcs = [fil]
                    target = self.installdir
                else:
                    self.log.error("Found neither string nor tuple as file to copy: '%s' (type %s)" % (fil, type(fil)))

                if not os.path.exists(target):
                    os.makedirs(target)
                for src in srcs:
                    src = os.path.join(self.cfg['start_dir'], src)
                    # copy individual file
                    if os.path.isfile(src):
                        self.log.debug("Copying file %s to %s" % (src, target))
                        shutil.copy2(src, target)
                    # copy directory
                    elif os.path.isdir(src):
                        self.log.debug("Copying directory %s to %s" % (src, target))
                        shutil.copytree(src, os.path.join(target, os.path.basename(src)))
                    else:
                        self.log.error("Can't copy non-existing path %s to %s" % (src, target))

        except OSError, err:
            self.log.error("Copying %s to installation dir failed: %s" % (fil, err))
