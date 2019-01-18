##
# Copyright 2016-2018 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
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
Style tests for easyconfig files. Uses pep8.

@author: Ward Poelmans (Ghent University)
"""

import glob
import sys
from unittest import TestCase, TestLoader, main
from vsc.utils import fancylogger

from easybuild.framework.easyconfig.tools import get_paths_for
from easybuild.framework.easyconfig.style import check_easyconfigs_style

try:
    import pep8
except ImportError:
    pass


class StyleTest(TestCase):
    log = fancylogger.getLogger("StyleTest", fname=False)

    def test_style_conformance(self):
        """Check the easyconfigs for style"""
        if 'pep8' not in sys.modules:
            print "Skipping style checks (no pep8 available)"
            return

        # all available easyconfig files
        easyconfigs_path = get_paths_for("easyconfigs")[0]
        specs = glob.glob('%s/*/*/*.eb' % easyconfigs_path)
        specs = sorted(specs)

        result = check_easyconfigs_style(specs)

        self.assertEqual(result, 0, "Found code style errors (and/or warnings): %s" % result)


def suite():
    """Return all style tests for easyconfigs."""
    return TestLoader().loadTestsFromTestCase(StyleTest)


if __name__ == '__main__':
    main()
