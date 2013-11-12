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
EasyBuild support for building and installing libint2, implemented as an easyblock

@author: Toon Verstraelen (Ghent University)
@author: Ward Poelmans (Ghent University)
"""

import os.path

from easybuild.easyblocks.generic.configuremake import ConfigureMake


class EB_libint2(ConfigureMake):
    def configure_step(self):
        """Add some extra configure options."""

        if self.toolchain.options['pic']:
            # Enforce consistency.
            self.cfg.update('configopts', "--with-pic")

        # The code in libint is automatically generated and hence it is in some
        # parts so compex that -O2 or -O3 compiler optimization takes forever.
        self.cfg.update('configopts', "--with-cxx-optflags='-O1'")

        # Also build shared libraries. (not enabled by default)
        self.cfg.update('configopts', "--enable-shared")

        super(EB_libint2, self).configure_step()

    def sanity_check_step(self):
        """Custom sanity check for Libint2."""

        custom_paths = {
            'files': ['lib/libint2.a', 'lib/libint2.so', 'include/libint2/libint2.h'],
            'dirs': [],
        }
        super(EB_libint2, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Specify correct CPATH for this installation."""
        guesses = super(EB_libint2, self).make_module_req_guess()
        guesses.update({
            'CPATH': ["include", os.path.join("include", "libint2")],
        })
        return guesses
