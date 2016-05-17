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
Support for building and installing GenomeAnalysisTK, implemented as an easyblock.
DEPRECATED, use generic Tarball easyblock instead.

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os
import shutil

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError


class EB_GenomeAnalysisTK(EasyBlock):
    """
    Support for building and installing GenomeAnalysisTK.
    DEPRECATED, use generic Tarball easyblock instead.
    """

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(EB_GenomeAnalysisTK, self).__init__(*args, **kwargs)
        self.log.deprecated("Use the generic Tarball easyblock rather than this software-specific easyblock", '3.0')

    def configure_step(self):
        """No configure step for GenomeAnalysisTK"""
        pass

    def build_step(self):
        """No build step for GenomeAnalysisTK"""
        pass

    def install_step(self):
        """Install GenomeAnalysisTK by copying required files/directories"""
        srcdir = self.cfg['start_dir']
        for jar in ["AnalyzeCovariates.jar", "GenomeAnalysisTK.jar"]:
            src = os.path.join(srcdir, jar)
            dst = os.path.join(self.installdir, jar)
            try:
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    self.log.info("Successfully copied %s to %s" % (src, dst))
            except OSError, err:
                raise EasyBuildError("Failed to copy %s to %s: %s", src, dst, err)

        for subdir in ['resources']:
            try:
                src_dir = os.path.join(self.cfg['start_dir'], subdir)
                dst_dir = os.path.join(self.installdir, subdir)
                if os.path.exists(src_dir):
                    shutil.copytree(src_dir, dst_dir)
                else:
                    self.log.warning("No directory %s, so not copying it." % src_dir)
                self.log.info("Successfully copied %s to %s" % (src_dir, dst_dir))
            except OSError, err:
                raise EasyBuildError("Failed to copy %s to %s: %s", src_dir, dst_dir, err)

    def sanity_check_step(self):
        """Custom sanity check for GenomeAnalysisTK"""
        custom_paths = {
            'files': ["GenomeAnalysisTK.jar"],
            'dirs': ["resources"],
        }
        super(EB_GenomeAnalysisTK, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Add module entries specific to GenomeAnalysisTK"""
        txt = super(EB_GenomeAnalysisTK, self).make_module_extra()
        txt += self.module_generator.prepend_paths('PATH', '')
        return txt

