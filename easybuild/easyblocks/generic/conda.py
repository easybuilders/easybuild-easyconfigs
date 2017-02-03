##
# Copyright 2009-2017 Ghent University
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
EasyBuild support for installing software using 'conda', implemented as an easyblock.

@author: Jillian Rowe (New York University Abu Dhabi)
@author: Kenneth Hoste (HPC-UGent)
"""

import os

from easybuild.easyblocks.generic.binary import Binary
from easybuild.framework.easyconfig import CUSTOM
import easybuild.tools.environment as env
from easybuild.tools.run import run_cmd


class Conda(Binary):
    """Support for installing software using 'conda'."""

    @staticmethod
    def extra_options(extra_vars=None):
        """Extra easyconfig parameters specific to Conda easyblock."""
        extra_vars = Binary.extra_options(extra_vars)
        extra_vars.update({
            'channels': [None, "List of conda channels to pass to 'conda install'", CUSTOM],
            'environment_file': [None, "Conda environment.yml file to use with 'conda env create'", CUSTOM],
            'remote_environment': [None, "Remote conda environment to use with 'conda env create'", CUSTOM],
            'requirements': [None, "Requirements specification to pass to 'conda install'", CUSTOM],
        })
        return extra_vars

    def extract_step(self):
        """Copy sources via extract_step of parent, if any are specified."""
        if self.src:
            super(Conda, self).extract_step()

    def set_conda_env(self):
        """Set up environment for using 'conda'."""
        env.setvar('CONDA_ENV', self.installdir)
        env.setvar('CONDA_DEFAULT_ENV', self.installdir)

    def install_step(self):
        """Install software using 'conda env create' or 'conda create' & 'conda install'."""

        # initialize conda environment
        # setuptools is just a choice, but *something* needs to be there
        cmd = "conda config --add create_default_packages setuptools"
        run_cmd(cmd, log_all=True, simple=True)

        if self.cfg['environment_file'] or self.cfg['remote_environment']:

            if self.cfg['environment_file']:
                env_spec = '-f ' + self.cfg['environment_file']
            else:
                env_spec = self.cfg['remote_environment']

            self.set_conda_env()

            # use --force to ignore existing installation directory
            cmd = "%s conda env create --force %s -p %s" % (self.cfg['preinstallopts'], env_spec, self.installdir)
            run_cmd(cmd, log_all=True, simple=True)

        else:
            cmd = "%s conda create --force -y -p %s" % (self.cfg['preinstallopts'], self.installdir)
            run_cmd(cmd, log_all=True, simple=True)

            if self.cfg['requirements']:
                self.set_conda_env()

                install_args = "-y %s " % self.cfg['requirements']
                if self.cfg['channels']:
                    install_args += ' '.join('-c ' + chan for chan in self.cfg['channels'])

                cmd = "conda install %s" % (install_args)
                run_cmd(cmd, log_all=True, simple=True)

                self.log.info("Installed conda requirements")

    def make_module_extra(self):
        """Add the install directory to the PATH."""
        txt = super(Conda, self).make_module_extra()
        txt += self.module_generator.set_environment('CONDA_ENV', self.installdir)
        txt += self.module_generator.set_environment('CONDA_DEFAULT_ENV', self.installdir)
        self.log.debug("make_module_extra added this: %s", txt)
        return txt

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for.
        """
        # LD_LIBRARY_PATH issue discusses here
        # http://superuser.com/questions/980250/environment-module-cannot-initialize-tcl
        return {
            'PATH': ['bin', 'sbin'],
            'MANPATH': ['man', os.path.join('share', 'man')],
            'PKG_CONFIG_PATH': [os.path.join(x, 'pkgconfig') for x in ['lib', 'lib32', 'lib64', 'share']],
        }
