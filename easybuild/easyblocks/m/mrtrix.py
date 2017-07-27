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
# https://github.com/easybuilders/easybuild
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
import shutil
from distutils.version import LooseVersion

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_MRtrix(EasyBlock):
    """Support for building/installing MRtrix."""

    def __init__(self, *args, **kwargs):
        """Initialize easyblock, enable build-in-installdir based on version."""
        super(EB_MRtrix, self).__init__(*args, **kwargs)

        if LooseVersion(self.version) >= LooseVersion('0.3') and LooseVersion(self.version) < LooseVersion('0.3.14'):
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
            if LooseVersion(self.version) < LooseVersion('0.3.13'):
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

        elif LooseVersion(self.version) >= LooseVersion('0.3.14'):
            release_dir = os.path.join(self.builddir, 'release')
            scripts_dir = os.path.join(self.builddir, 'scripts')
            try:
                os.rmdir(self.installdir)
                shutil.copytree(release_dir, self.installdir)
                shutil.copytree(scripts_dir, os.path.join(self.installdir, 'scripts'))
                # some scripts expect 'release/bin' to be there, so we put a symlink in place
                os.symlink(self.installdir, os.path.join(self.installdir, 'release'))
            except OSError as err:
                raise EasyBuildError("Failed to copy %s & %s to %s: %s", release_dir, scripts_dir, self.installdir, err)

    def make_module_req_guess(self):
        """
        Return list of subdirectories to consider to update environment variables;
        also consider 'scripts' subdirectory for $PATH
        """
        guesses = super(EB_MRtrix, self).make_module_req_guess()
        guesses['PATH'].append('scripts')
        return guesses

    def sanity_check_step(self):
        """Custom sanity check for MRtrix."""
        shlib_ext = get_shared_lib_ext()

        if LooseVersion(self.version) >= LooseVersion('0.3'):
            libso = 'libmrtrix.%s' % shlib_ext
        else:
            libso = 'libmrtrix-%s.%s' % ('_'.join(self.version.split('.')), shlib_ext)
        custom_paths = {
            'files': [os.path.join('lib', libso)],
            'dirs': ['bin'],
        }
        super(EB_MRtrix, self).sanity_check_step(custom_paths=custom_paths)
