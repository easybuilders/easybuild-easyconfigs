##
# Copyright 2016 Ghent University
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
Style tests for easyconfig files. Uses pep8.

@author: Ward Poelmans (Ghent University)
"""

from unittest import TestCase, TestLoader, main
import glob
import re
import sys
from vsc.utils import fancylogger

from easybuild.framework.easyconfig.tools import get_paths_for

try:
    import pep8
except ImportError:
    pass


# any function starting with eb_check_ will be added to the tests
# if the test number is added to the select list. The test number is
# definied as AXXX where XXX is a 3 digit number. It should be mentioned
# in the docstring as a single word.
def eb_check_trailing_whitespace(physical_line, lines, line_number, total_lines):
    """
    W299
    Warn about trailing whitespace, expect for the description and comments.
    This differs from the standard trailing whitespace check as that
    will will warn for any trailing whitespace.
    """
    comment_re = re.compile('^\s*#')
    if comment_re.match(physical_line):
        return None

    result = pep8.trailing_whitespace(physical_line)
    if result:
        result = (result[0], result[1].replace("W291", "W299"))

    # if the warning is about the multiline string of description
    # we will not issue a warning
    keys_re = re.compile("^(?P<key>[a-z_]+)\s*=\s*")

    for line in reversed(lines[0:line_number]):
        res = keys_re.match(line)
        if res:
            if res.group("key") == "description":
                return None
            else:
                break

    return result


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

        # register the extra checks before using pep8
        cands = globals()
        for check_function in sorted([cands[f] for f in cands if callable(cands[f]) and f.startswith('eb_check_')]):
            pep8.register_check(check_function)

        pep8style = pep8.StyleGuide(quiet=False, config_file=None)
        options = pep8style.options
        options.max_line_length = 120
        # currently, we only check a selected set of tests
        options.ignore = ('',)
        options.select = ('E101',  # indentation contains mixed spaces and tabs
                          'E111',  # indentation is not a multiple of four
                          'W191',  # indentation contains tabs
                          # 'E303',  # too many blank lines (3)
                          # 'E501',  # line too long
                          # 'W291',  # trailing whitespace
                          'W293',  # blank line contains whitespace
                          'W299',  # trailing whitespace, EB style
                          )

        result = pep8style.check_files(specs)
        result.print_statistics()
        self.assertEqual(result.total_errors, 0,
                         "Found code style errors (and/or warnings).")


def suite():
    """Return all style tests for easyconfigs."""
    return TestLoader().loadTestsFromTestCase(StyleTest)


if __name__ == '__main__':
    main()
