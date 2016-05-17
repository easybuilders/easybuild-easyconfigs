##
# Copyright 2015-2016 Ghent University
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
EasyBuild support for Ruby, implemented as an easyblock

@author: Robert Schmidt (Ottawa Hospital Research Institute)
"""

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.systemtools import get_shared_lib_ext


# seems like the quickest test for whether a gem is installed
EXTS_FILTER_GEMS = ("gem list '^%(ext_name)s$' -i", "")


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
            'files': ['bin/erb', 'bin/gem', 'bin/irb', 'bin/rake', 'bin/rdoc', 'bin/ri', 'bin/ruby',
                      'lib/libruby.%s' % get_shared_lib_ext()],
            'dirs': ['include/ruby-%s.0' % majver, 'lib/pkgconfig', 'lib/ruby/%s.0' % majver, 'lib/ruby/gems'],
        }
        return super(EB_Ruby, self).sanity_check_step(custom_paths=custom_paths)
