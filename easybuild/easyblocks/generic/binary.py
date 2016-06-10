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
General EasyBuild support for software with a binary installer

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import shutil
import os
import stat

from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import mkdir, rmtree2
from easybuild.tools.run import run_cmd


class Binary(EasyBlock):
    """
    Support for installing software that comes in binary form.
    Just copy the sources to the install dir, or use the specified install command.
    """

    @staticmethod
    def extra_options(extra_vars=None):
        """Extra easyconfig parameters specific to Binary easyblock."""
        extra_vars = EasyBlock.extra_options(extra_vars)
        extra_vars.update({
            'install_cmd': [None, "Install command to be used.", CUSTOM],
            # staged installation can help with the hard (potentially faulty) check on available disk space
            'staged_install': [False, "Perform staged installation via subdirectory of build directory", CUSTOM],
        })
        return extra_vars

    def __init__(self, *args, **kwargs):
        """Initialize Binary-specific variables."""
        super(Binary, self).__init__(*args, **kwargs)

        self.actual_installdir = None
        if self.cfg['staged_install']:
            self.actual_installdir = self.installdir
            self.installdir = os.path.join(self.builddir, 'staged')
            mkdir(self.installdir, parents=True)
            self.log.info("Performing staged installation via %s" % self.installdir)

    def extract_step(self):
        """Move all source files to the build directory"""

        self.src[0]['finalpath'] = self.builddir

        # copy source to build dir.
        for source in self.src:
            src = source['path']
            dst = os.path.join(self.builddir, source['name'])
            try:
                shutil.copy2(src, self.builddir)
                os.chmod(dst, stat.S_IRWXU)
            except (OSError, IOError), err:
                raise EasyBuildError("Couldn't copy %s to %s: %s", src, self.builddir, err)

    def configure_step(self):
        """No configuration, this is binary software"""
        pass

    def build_step(self):
        """No compilation, this is binary software"""
        pass

    def install_step(self):
        """Copy all files in build directory to the install directory"""
        if self.cfg['install_cmd'] is None:
            try:
                # shutil.copytree doesn't allow the target directory to exist already
                rmtree2(self.installdir)
                shutil.copytree(self.cfg['start_dir'], self.installdir)
            except OSError, err:
                raise EasyBuildError("Failed to copy %s to %s: %s", self.cfg['start_dir'], self.installdir, err)
        else:
            cmd = ' '.join([self.cfg['preinstallopts'], self.cfg['install_cmd'], self.cfg['installopts']])
            self.log.info("Installing %s using command '%s'..." % (self.name, cmd))
            run_cmd(cmd, log_all=True, simple=True)

    def post_install_step(self):
        """Copy installation to actual installation directory in case of a staged installation."""
        if self.cfg['staged_install']:
            staged_installdir = self.installdir
            self.installdir = self.actual_installdir
            try:
                # copytree expects target directory to not exist yet
                if os.path.exists(self.installdir):
                    rmtree2(self.installdir)
                shutil.copytree(staged_installdir, self.installdir)
            except OSError, err:
                raise EasyBuildError("Failed to move staged install from %s to %s: %s",
                                     staged_installdir, self.installdir, err)

        super(Binary, self).post_install_step()

    def make_module_extra(self):
        """Add the install directory to the PATH."""

        txt = super(Binary, self).make_module_extra()
        txt += self.module_generator.prepend_paths("PATH", [''])
        self.log.debug("make_module_extra added this: %s" % txt)
        return txt
