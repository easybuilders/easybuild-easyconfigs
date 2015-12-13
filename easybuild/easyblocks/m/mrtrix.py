##
# Copyright 2009-2015 Ghent University
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
EasyBuild support for building and installing MRtrix, implemented as an easyblock
"""
import os
from distutils.version import LooseVersion

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.run import run_cmd


class EB_MRtrix(EasyBlock):
    """Support for building/installing MRtrix."""

    def __init__(self, *args, **kwargs):
        """Initialize easyblock, enable build-in-installdir based on version."""
        super(EB_MRtrix, self).__init__(*args, **kwargs)

        if LooseVersion(self.version) >= LooseVersion('0.3'):
            self.build_in_installdir = True
            self.log.debug("Enabled build-in-installdir for version %s", self.version)

    def extract_step(self):
        """Extract MRtrix sources."""
        # strip off 'mrtrix*' part to avoid having everything in a 'mrtrix*' subdirectory
        if LooseVersion(self.version) >= LooseVersion('0.3'):
            self.cfg.update('unpack_options', '--strip-components=1')

        super(EB_MRtrix, self).extract_step()

    def configure_step(self):
        """No configuration step for MRtrix."""
        if LooseVersion(self.version) >= LooseVersion('0.3'):
            env.setvar('LD', "%s LDFLAGS OBJECTS -o EXECUTABLE" % os.getenv('CXX'))
            env.setvar('LDLIB', "%s -shared LDLIB_FLAGS OBJECTS -o LIB" % os.getenv('CXX'))
            env.setvar('QMAKE_CXX', os.getenv('CXX'))
            cmd = "python configure -verbose"
            run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def build_step(self):
        """Custom build procedure for MRtrix."""
        cmd = "python build -verbose"
        run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def install_step(self):
        """Custom install procedure for MRtrix."""
        if LooseVersion(self.version) < LooseVersion('0.3'):
            cmd = "python build -verbose install=%s linkto=" % self.installdir
            run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def sanity_check_step(self):
        """Custom sanity check for MRtrix."""
        if LooseVersion(self.version) >= LooseVersion('0.3'):
            libso = 'libmrtrix.so'
        else:
            libso = 'libmrtrix-%s.so' % '_'.join(self.version.split('.'))
        custom_paths = {
            'files': [os.path.join('lib', libso)],
            'dirs': ['bin'],
        }
        super(EB_MRtrix, self).sanity_check_step(custom_paths=custom_paths)
