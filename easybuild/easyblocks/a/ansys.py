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
EasyBuild support for installing ANSYS, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
@author: Bart Verleye (Centre for eResearch, Auckland)
"""
import os
import stat

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.run import run_cmd
from easybuild.tools.filetools import adjust_permissions


class EB_ANSYS(EasyBlock):
    """Support for installing ANSYS."""

    def __init__(self, *args, **kwargs):
        """Initialize ANSYS-specific variables."""
        super(EB_ANSYS, self).__init__(*args, **kwargs)
        self.ansysver = "v%s" % ''.join(self.version.split('.')[0:2])

    def configure_step(self):
        """No configuration for ANSYS."""
        pass

    def build_step(self):
        """No building for ANSYS."""
        pass

    def install_step(self):
        """Custom install procedure for ANSYS."""
        licserv = self.cfg['license_server']
        licport = self.cfg['license_server_port']

        cmd = "./INSTALL -silent -install_dir %s -licserverinfo %s:%s" % (self.installdir, licport, licserv)
        run_cmd(cmd, log_all=True, simple=True)

        adjust_permissions(self.installdir, stat.S_IWOTH, add=False)

    def make_module_req_guess(self):
        """Custom extra module file entries for ANSYS."""
        guesses = super(EB_ANSYS, self).make_module_req_guess()
        dirs = [
            "tgrid/bin",
            "Framework/bin/Linux64",
            "aisol/bin/linx64",
            "RSM/bin",
            "ansys/bin",
            "autodyn/bin",
            "CFD-Post/bin",
            "CFX/bin",
            "fluent/bin",
            "TurboGrid/bin",
            "polyflow/bin",
            "Icepak/bin",
            "icemcfd/linux64_amd/bin"
        ]
        guesses.update({"PATH": [os.path.join(self.ansysver, dir) for dir in dirs]})
        return guesses

    def make_module_extra(self):
        """Define extra environment variables required by Ansys"""
        txt = super(EB_ANSYS, self).make_module_extra()
        icem_acn = os.path.join(self.installdir, 'icemcfd', 'linux64_amd')
        txt += self.module_generator.set_environment('ICEM_ACN', icem_acn)
        return txt

    def sanity_check_step(self):
        """Custom sanity check for ANSYS."""
        custom_paths = {
           'files': [os.path.join(self.ansysver, "fluent", "bin", "fluent%s" % x) for x in ['', '_arch', '_sysinfo']],
           'dirs': [os.path.join(self.ansysver, x) for x in ["ansys", "aisol", "CFD-Post","CFX"]]
        }
        super(EB_ANSYS, self).sanity_check_step(custom_paths=custom_paths)
