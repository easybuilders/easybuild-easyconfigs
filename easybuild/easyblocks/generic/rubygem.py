##
# Copyright 2015-2015 Ghent University
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
EasyBuild support for Ruby Gems, implemented as an easyblock

@author: Robert Schmidt (Ottawa Hospital Research Institute)
"""
import shutil

import easybuild.tools.environment as env
from easybuild.framework.extensioneasyblock import ExtensionEasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd


class RubyGem(ExtensionEasyBlock):
    """Builds and installs Ruby Gems."""

    def __init__(self, *args, **kwargs):
        """RubyGem easyblock constructor."""
        super(RubyGem, self).__init__(*args, **kwargs)
        self.ext_src = None

    def run(self):
        """Perform the actual Ruby gem build/install"""
        if not self.src:
            raise EasyBuildError("No source found for Ruby Gem %s, required for installation.", self.name)

        super(RubyGem, self).run()

        self.ext_src = self.src
        self.log.debug("Installing Ruby gem %s version %s." % (self.name, self.version))
        self.install_step()

    def extract_step(self):
        """Skip extraction, gemfiles will be installed as downloaded"""
        if len(self.src) > 1:
            raise EasyBuildError("Don't know how to handle Ruby gems with multiple sources.'")
        else:
            try:
                shutil.copy2(self.src[0]['path'], self.builddir)
            except OSError, err:
                raise EasyBuildError("Failed to copy source to build dir: %s", err)
            self.ext_src = self.src[0]['name']

            # set final path since it can't be determined from unpacked sources (used for guessing start_dir)
            self.src[0]['finalpath'] = self.builddir

    def configure_step(self):
        """No separate configuration for Ruby Gems."""
        pass

    def build_step(self):
        """No separate build procedure for Ruby Gems."""
        pass

    def test_step(self):
        """No separate (standard) test procedure for Ruby Gems."""
        pass

    def install_step(self):
        """Install Ruby Gems using gem package manager"""
        ruby_root = get_software_root('Ruby')
        if not ruby_root:
            raise EasyBuildError("Ruby module not loaded?")
        env.setvar('GEM_HOME', self.installdir)
        run_cmd("gem install --install-dir %s --local %s" % (ruby_root, self.ext_src))
