##
# Copyright 2016-2024 Ghent University
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
from unittest import TestLoader, main, skipIf

from easybuild.base import fancylogger
from easybuild.base.testing import TestCase
from easybuild.framework.easyconfig.tools import get_paths_for
from easybuild.framework.easyconfig.style import check_easyconfigs_style

try:
    import pep8
except ImportError:
    pep8 = None


class StyleTest(TestCase):
    log = fancylogger.getLogger("StyleTest", fname=False)

    @skipIf(not pep8, 'no pep8 available')
    def test_style_conformance(self):
        """Check the easyconfigs for style"""
        # all available easyconfig files
        easyconfigs_path = get_paths_for("easyconfigs")[0]
        specs = glob.glob('%s/*/*/*.eb' % easyconfigs_path)
        specs = sorted(specs)

        self.mock_stderr(True)
        self.mock_stdout(True)
        result = check_easyconfigs_style(specs)
        stderr, stdout = self.get_stderr(), self.get_stdout()
        self.mock_stderr(False)
        self.mock_stdout(False)

        error_msg = '\n'.join([
            "There shouldn't be any code style errors (and/or warnings), found %d:" % result,
            stdout,
            stderr,
        ])
        self.assertEqual(result, 0, error_msg)


def suite(loader=None):
    """Return all style tests for easyconfigs."""
    if not loader:
        loader = TestLoader()
    return loader.loadTestsFromTestCase(StyleTest)


if __name__ == '__main__':
    main()
