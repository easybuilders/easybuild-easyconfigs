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
EasyBuild support for Ruby, implemented as an easyblock

@author: Robert Schmidt (Ottawa Hospital Research Institute)
@author: Kenneth Hoste (Ghent University)
"""
import os

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.systemtools import get_shared_lib_ext


# seems like the quickest test for whether a gem is installed
EXTS_FILTER_GEMS = ("gem list %(ext_name)s -i", "")


class EB_Ruby(ConfigureMake):
    """Building and installing Ruby including support for gems"""
    
    def prepare_for_extensions(self):
        """Sets default class and filter for gems"""
        self.cfg['exts_defaultclass'] = 'RubyGem'
        self.cfg['exts_filter'] = EXTS_FILTER_GEMS

    def configure_step(self):
        """Updates configure options for the Ruby base install"""

        self.cfg.update('configopts', "--disable-install-doc --enable-shared")
        super(EB_Ruby, self).configure_step()

    def sanity_check_step(self):
        """Custom sanity check for Ruby gems"""
        majver = '.'.join(self.version.split('.')[:2])
        custom_paths = {
            'files': ['bin/ruby', 'bin/rake', 'bin/gem', 'bin/testrb', 'bin/erb',
                      'bin/ri', 'bin/irb', 'bin/rdoc', 'lib/libruby.%s' % get_shared_lib_ext()],
            'dirs': ['lib/ruby/%s.0' % majver, 'lib/ruby/gems', 'lib/pkgconfig',
                     'include/ruby-%s.0' % majver],
        }
        return super(EB_Ruby, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Define $GEM_PATH in module file."""
        txt = super(EB_Ruby, self).make_module_extra()
        maj_min_ver = '.'.join(self.version.split('.')[:2])
        gems_dir = os.path.join(self.installdir, 'lib', 'ruby', 'gems', '%s.0' % maj_min_ver, 'gems')
        txt += self.module_generator.set_environment('GEM_PATH', gems_dir)
        return txt
