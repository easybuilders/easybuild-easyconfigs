##
# Copyright 2016-2016 Ghent University
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
EasyBuild support for building and installing ADF, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os
import shutil

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class EB_ADF(EasyBlock):
    """Support for building/installing ADF."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for ADF."""
        super(EB_ADF, self).__init__(*args, **kwargs)

        self.build_in_installdir = True

    def extract_step(self):
        """Extract sources."""
        # strip off 'adf<version>' part to avoid having everything in a subdirectory
        self.cfg['unpack_options'] = "--strip-components=1"
        super(EB_ADF, self).extract_step()

    def configure_step(self):
        """Custom configuration procedure for ADF."""

        env.setvar('ADFHOME', self.installdir)
        env.setvar('ADFBIN', os.path.join(self.installdir, 'bin'))
        env.setvar('ADFRESOURCES', os.path.join(self.installdir, 'atomicdata'))
        if self.cfg['license_file'] and os.path.exists(self.cfg['license_file']):
            env.setvar('SCMLICENSE', self.cfg['license_file'])
        else:
            raise EasyBuildError("No or non-existing license file specified: %s", self.cfg['license_file'])

        cmd = './Install/configure'
        run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def build_step(self):
        """No separate custom build procedure for ADF, see install step."""
        pass

    def install_step(self):
        """Custom install procedure for ADF."""

        # bin/init.sh is required to build, so copy it from Install/init.sh
        src_init_path = os.path.join('Install', 'init.sh')
        target_init_path = os.path.join('bin', 'init.sh')
        try:
            shutil.copy2(src_init_path, target_init_path)
        except OSError as err:
            raise EasyBuildError("Failed to copy %s to %s: %s", src_init_path, target_init_path, err)

        cmd = "./bin/foray -j %d" % self.cfg['parallel']
        run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def sanity_check_step(self):
        """Custom sanity check for ADF."""
        custom_paths = {
            'files': ['bin/adf'],
            'dirs': ['atomicdata', 'examples'],
        }
        super(EB_ADF, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Custom extra module file entries for ADF."""
        txt = super(EB_ADF, self).make_module_extra()

        txt += self.module_generator.set_environment('ADFHOME', self.installdir)
        txt += self.module_generator.set_environment('ADFBIN', os.path.join(self.installdir, 'bin'))
        txt += self.module_generator.set_environment('ADFRESOURCES', os.path.join(self.installdir, 'atomicdata'))

        return txt
