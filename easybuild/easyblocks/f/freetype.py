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
EasyBuild support for building and installing freetype, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_freetype(ConfigureMake):
    """Support for building/installing freetype."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for freetype."""
        super(EB_freetype, self).__init__(*args, **kwargs)

        self.maj_ver = self.version.split('.')[0]

    def sanity_check_step(self):
        """Custom sanity check for freetype."""
        custom_paths = {
            'files': ['bin/freetype-config', 'lib/libfreetype.a', 'lib/libfreetype.%s' % get_shared_lib_ext(),
                      'lib/pkgconfig/freetype%s.pc' % self.maj_ver],
            'dirs': ['include/freetype%s' % self.maj_ver],
        }
        super(EB_freetype, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Custom guess for CPATH for freetype."""

        guesses = super(EB_freetype, self).make_module_req_guess()

        guesses.update({
                        'CPATH': ['include/freetype%s' % self.maj_ver],
                       })

        return guesses
