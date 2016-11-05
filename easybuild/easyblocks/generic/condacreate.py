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
EasyBuild support for building and installing conda environments via conda create -p, implemented as an easyblock
@author: Jillian Rowe (New York University Abu Dhabi)
"""

import os

from easybuild.easyblocks.anaconda import initialize_conda_env, set_conda_env
from easybuild.easyblocks.generic.binary import Binary
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.run import run_cmd


class CondaCreate(Binary):
    """Support for building/installing CondaCreate."""

    @staticmethod
    def extra_options(extra_vars=None):
        """Extra easyconfig parameters specific to EB_CondaCreate easyblock."""
        extra_vars = Binary.extra_options(extra_vars)
        extra_vars.update({
            'channels': [None, "Custom conda channels", CUSTOM],
            'post_install_cmd': [None, "Commands after install: pip install, cpanm install, etc", CUSTOM],
            'pre_install_cmd': [None, "Commands before install: setting environment variables, etc", CUSTOM],
            'requirements': [None, "Requirements file", CUSTOM],
        })
        return extra_vars

    def extract_step(self):
        """No sources expected."""
        if self.src:
            super(EB_CondaCreate, self).extract_step()
        else:
            pass

    def install_step(self):
        """Set up conda environment using 'conda create' and install using specified requirements."""

        if self.cfg['pre_install_cmd']:
            run_cmd(self.cfg['pre_install_cmd'], log_all=True, simple=True)

        initialize_conda_env(self.installdir)

        cmd = "conda create -y -p %s" % self.installdir
        run_cmd(cmd, log_all=True, simple=True)

        if self.cfg['requirements']:
            set_conda_env(self.installdir)

            if self.cfg['channels'] and self.cfg['requirements']:
                cmd = "conda install -y -c %s %s" % (self.cfg['channels'], self.cfg['requirements'])
            elif self.cfg['requirements']:
                cmd = "conda install -y %s" % self.cfg['requirements']

            run_cmd(cmd, log_all=True, simple=True)
            self.log.info('Installed conda requirements')

        if self.cfg['post_install_cmd']:
            run_cmd(self.cfg['post_install_cmd'], log_all=True, simple=True)

    def make_module_extra(self):
        """Add the install directory to the PATH."""
        txt = super(CondaCreate, self).make_module_extra()
        txt += self.module_generator.set_environment('CONDA_ENV', self.installdir)
        txt += self.module_generator.set_environment('CONDA_DEFAULT_ENV', self.installdir)
        self.log.debug("make_module_extra added this: %s", txt)
        return txt

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for.
        """
        return {
            'PATH': ['bin', 'sbin'],
            'MANPATH': ['man', os.path.join('share', 'man')],
            'PKG_CONFIG_PATH': [os.path.join(x, 'pkgconfig') for x in ['lib', 'lib32', 'lib64', 'share']],
        }
