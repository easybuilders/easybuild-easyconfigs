##
# Copyright 2013 Ghent University
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
EasyBuild support for building and installing FDTD Solutions, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import run_cmd_qa


class EB_FDTD_underscore_Solutions(EasyBlock):
    """Support for building/installing FDTD Solutions."""

    def configure_step(self):
        """No configuration for FDTD Solutions."""
        pass

    def build_step(self):
        """No build step for FDTD Solutions."""
        pass

    def install_step(self):
        """Install FDTD Solutions using install.sh script."""
        cmd = "./install.sh"
        acceptq = ''.join([
            "If you accept the terms above, type ACCEPT, otherwise press <enter> ",
            "to cancel the install [REJECT]:"
        ])
        qa = {
            acceptq: "ACCEPT",
            "Please select an option from the list [1]:": '1',
            "Please enter the install directory [/opt/lumerical/fdtd]:": self.installdir,
        }
        no_qa = [
        ]
        std_qa = {
            "Press <enter> to continue.*": ''
        }
        run_cmd_qa(cmd, qa, no_qa=no_qa, std_qa=std_qa, log_all=True, simple=True)

    def make_module_req_guess(self):
        """Adjust values for PATH, LD_LIBRARY_PATH, etc."""
        guesses = super(EB_FDTD_underscore_Solutions, self).make_module_req_guess()
        guesses.update({
            'PATH': ['opt/lumerical/fdtd/bin'],
            'LD_LIBRARY_PATH': ['opt/lumerical/fdtd/lib'],
        })
        return guesses

    def sanity_check_step(self):
        """Custom sanity check for FDTD Solutions."""
        custom_paths = {
            'files': [],
            'dirs': ['opt/lumerical/fdtd/bin', 'opt/lumerical/fdtd/lib'],
        }
        super(EB_FDTD_underscore_Solutions, self).sanity_check_step(custom_paths=custom_paths)
