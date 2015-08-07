##
# Copyright 2015 Bart Oldeman
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

from easybuild.easyblocks.generic.tarball import Tarball
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd

class EB_pgi(Tarball):
    """
    Support for installing the PGI compilers
    """

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for.
        """
        dirs = super(EB_pgi, self).make_module_req_guess()
        prefix = os.path.join('linux86-64', self.version)
        for key in dirs:
            dirs[key] = [os.path.join(prefix, d) for d in dirs[key]]
        return dirs

    def sanity_check_step(self):
        """Custom sanity check for PGI"""

        prefix = os.path.join('linux86-64', self.version)
        custom_paths = {
                        'files': [os.path.join(prefix, "bin", "pgcc")],
                        'dirs': [os.path.join(prefix, "bin"), os.path.join(prefix, "lib"),
                                 os.path.join(prefix, "include"), os.path.join(prefix, "man")]
                       }

        super(EB_pgi, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Overwritten from Application to add extra txt"""
        txt = super(EB_pgi, self).make_module_extra()
        txt += self.module_generator.set_environment('PGI', self.installdir)
        return txt

    def install_step(self):
        """Install by running install command."""

        # make sure localrc uses GCC in PATH, not always the system GCC
        cmd = "sed -i 's/^PATH/#PATH/' install"
        run_cmd(cmd, log_all=True, simple=True)
        cmd = "sed -i 's/^PATH/#PATH/' %s" % os.path.join("linux86-64", self.version,
                                                          "bin", "makelocalrc")
        run_cmd(cmd, log_all=True, simple=True)

        cmd = 'PGI_SILENT=true PGI_ACCEPT_EULA=accept PGI_INSTALL_DIR=%s ' % self.installdir
        cmd += 'PGI_INSTALL_NVIDIA=true PGI_INSTALL_AMD=true PGI_INSTALL_JAVA=true '
        cmd += 'PGI_INSTALL_MANAGED=true '
        cmd += './install'

        run_cmd(cmd, log_all=True, simple=True)
        if self.cfg['license_file']:
            license_file = self.cfg['license_file']
            try:
                licfile = os.path.join(self.installdir, "license.dat")
                os.symlink(license_file, licfile)
            except OSError, err:
                raise EasyBuildError("Failed to symlink %s to %s: %s", licfile, license_file, err)
        else:
            raise EasyBuildError("Please specify a license_file location in your easyconfig")

