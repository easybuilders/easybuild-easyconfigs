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
EasyBuild support for building and installing Libint, implemented as an easyblock

@author: Toon Verstraelen (Ghent University)
@author: Ward Poelmans (Ghent University)
"""

import os.path
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_Libint(ConfigureMake):
    def configure_step(self):
        """Add some extra configure options."""

        # also build shared libraries (not enabled by default)
        self.cfg.update('configopts', "--enable-shared")

        if self.toolchain.options['pic']:
            # Enforce consistency.
            self.cfg.update('configopts', "--with-pic")

        if LooseVersion(self.version) >= LooseVersion('2.0'):
            # the code in libint is automatically generated and hence it is in some
            # parts so complex that -O2 or -O3 compiler optimization takes forever
            self.cfg.update('configopts', "--with-cxx-optflags='-O1'")

        super(EB_Libint, self).configure_step()

    def sanity_check_step(self):
        """Custom sanity check for Libint."""
        shlib_ext = get_shared_lib_ext()

        if LooseVersion(self.version) >= LooseVersion('2.0'):
            custom_paths = {
                'files': ['lib/libint2.a', 'lib/libint2.%s' % shlib_ext, 'include/libint2/libint2.h'],
                'dirs': [],
            }
        else:
            custom_paths = {
                'files': ['include/libint/libint.h', 'include/libint/hrr_header.h', 'include/libint/vrr_header.h',
                          'lib/libint.a', 'lib/libint.%s' % shlib_ext],
                'dirs': [],
            }
        super(EB_Libint, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Specify correct CPATH for this installation."""
        guesses = super(EB_Libint, self).make_module_req_guess()
        if LooseVersion(self.version) >= LooseVersion('2.0'):
            libint_include = os.path.join('include', 'libint2')
        else:
            libint_include = os.path.join('include', 'libint')
        guesses.update({
            'CPATH': ['include', libint_include],
        })
        return guesses
