##
# Copyright 2015-2015 Bart Oldeman
#
# This file is triple-licensed under GPLv2 (see below), MIT, and
# BSD three-clause licenses.
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
EasyBuild support for installing PGI compilers, implemented as an easyblock

@author: Bart Oldeman (McGill University, Calcul Quebec, Compute Canada)
"""
import os
import fileinput
import re
import sys

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd

class EB_pgi(EasyBlock):
    """
    Support for installing the PGI compilers
    """

    def __init__(self, *args, **kwargs):
        """Easyblock constructor, define custom class variables specific to PGI."""
        super(EB_pgi, self).__init__(*args, **kwargs)
        if not self.cfg['license_file']:
            self.cfg['license_file'] = 'UNKNOWN'
        self.install_subdir = os.path.join('linux86-64', self.version)

    def configure_step(self):
        """
        Dummy configure method, just a license check
        """
        if not os.path.exists(self.cfg['license_file']):
            raise EasyBuildError("Non-existing license file specified: %s", self.cfg['license_file'])

    def build_step(self):
        """
        Dummy build method: nothing to build
        """
        pass

    def install_step(self):
        """Install by running install command."""

        pgi_env_vars = {
            'PGI_ACCEPT_EULA': 'accept',
            'PGI_INSTALL_AMD': 'true',
            'PGI_INSTALL_DIR': self.installdir,
            'PGI_INSTALL_JAVA': 'true',
            'PGI_INSTALL_MANAGED': 'true',
            'PGI_INSTALL_NVIDIA': 'true',
            'PGI_SILENT': 'true',
            }
        cmd = "%s ./install" % ' '.join(['%s=%s' % x for x in sorted(pgi_env_vars.items())])
        run_cmd(cmd, log_all=True, simple=True)

        # make sure localrc uses GCC in PATH, not always the system GCC, and does not use a system g77 but gfortran
        install_abs_subdir = os.path.join(self.installdir, self.install_subdir)
        filename = os.path.join(install_abs_subdir, "bin", "makelocalrc")
        for line in fileinput.input(filename, inplace='1', backup='.orig'):
            line = re.sub(r"^PATH=/", r"#PATH=/", line)
            sys.stdout.write(line)

        cmd = "%s -x %s -g77 /" % (filename, install_abs_subdir)
        run_cmd(cmd, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for PGI"""
        prefix = self.install_subdir
        custom_paths = {
                        'files': [os.path.join(prefix, "bin", "pgcc")],
                        'dirs': [os.path.join(prefix, "bin"), os.path.join(prefix, "lib"),
                                 os.path.join(prefix, "include"), os.path.join(prefix, "man")]
                       }
        super(EB_pgi, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Prefix subdirectories in PGI install directory considered for environment variables defined in module file."""
        dirs = super(EB_pgi, self).make_module_req_guess()
        for key in dirs:
            dirs[key] = [os.path.join(self.install_subdir, d) for d in dirs[key]]
        return dirs

    def make_module_extra(self):
        """Add environment variables LM_LICENSE_FILE and PGI for license file and PGI location"""
        txt = super(EB_pgi, self).make_module_extra()
        txt += self.module_generator.prepend_paths('LM_LICENSE_FILE', [self.cfg['license_file']], allow_abs=True)
        txt += self.module_generator.set_environment('PGI', self.installdir)
        return txt
