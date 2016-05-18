##
# Copyright 2013 Ghent University
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
EasyBuild support for building and installing FDTD Solutions, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import glob
import os
import shutil
from easybuild.easyblocks.generic.rpm import rebuild_rpm
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd_qa


class EB_FDTD_underscore_Solutions(EasyBlock):
    """Support for building/installing FDTD Solutions."""

    def configure_step(self):
        """No configuration for FDTD Solutions."""
        pass

    def build_step(self):
        """No build step for FDTD Solutions."""
        # locate RPM and rebuild it to make it relocatable
        rpms = glob.glob(os.path.join(self.cfg['start_dir'], 'rpm_install_files', 'FDTD-%s*.rpm' % self.version))
        if len(rpms) != 1:
            raise EasyBuildError("Incorrect number of RPMs found, was expecting exactly one: %s", rpms)
        rebuilt_dir = os.path.join(self.cfg['start_dir'], 'rebuilt')
        rebuild_rpm(rpms[0], rebuilt_dir)

        # replace original RPM with relocatable RPM
        rebuilt_rpms = glob.glob(os.path.join(rebuilt_dir, '*', '*.rpm'))
        if len(rebuilt_rpms) != 1:
            raise EasyBuildError("Incorrect number of rebuilt RPMs found, was expecting exactly one: %s", rebuilt_rpms)

        try:
            os.rename(rpms[0], '%s.bk' % rpms[0])
            shutil.copy2(rebuilt_rpms[0], rpms[0])
        except OSError, err:
            raise EasyBuildError("Failed to replace original RPM with rebuilt RPM: %s", err)

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
