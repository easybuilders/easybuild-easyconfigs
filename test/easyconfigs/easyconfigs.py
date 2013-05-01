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
Unit tests for easyconfig files.

@author: Kenneth Hoste (Ghent University)
"""

import copy
import glob
import os
import re
import sys
import tempfile
from distutils.version import LooseVersion
from vsc import fancylogger
from vsc.utils.missing import nub
from unittest import TestCase, TestLoader, main

import easybuild.main as main
from easybuild.framework.easyblock import EasyBlock, get_class
from easybuild.framework.easyconfig.easyconfig import EasyConfig
from easybuild.framework.easyconfig.tools import get_paths_for
from easybuild.main import dep_graph, resolve_dependencies, process_easyconfig


class EasyConfigTest(TestCase):
    """Baseclass for easyconfig testcases."""
        
    log = fancylogger.getLogger("EasyConfigTest", fname=False)
    name_regex = re.compile("^name\s*=\s*['\"](.*)['\"]$", re.M)
    easyblock_regex = re.compile(r"^\s*easyblock\s*=['\"](.*)['\"]$", re.M)
    # make sure a logger is present for main
    main._log = log
    ordered_specs = None

    def process_all_easyconfigs(self):
        """Process all easyconfigs and resolve inter-easyconfig dependencies."""
        # all available easyconfig files
        easyconfigs_path = get_paths_for("easyconfigs")[0]
        specs = glob.glob('%s/*/*/*.eb' % easyconfigs_path)

        # parse all easyconfigs
        easyconfigs = []
        for spec in specs:
            easyconfigs.extend(process_easyconfig(spec, validate=False))

        self.ordered_specs = resolve_dependencies(easyconfigs, easyconfigs_path)

    # pygraph dependencies required for constructing dependency graph are not available prior to Python 2.6
    if LooseVersion(sys.version) >= LooseVersion('2.6'):
        def test_dep_graph(self):
            """Unit test that builds a full dependency graph."""
            # temporary file for dep graph
            (hn, fn) = tempfile.mkstemp(suffix='.dot')
            os.close(hn)

            if self.ordered_specs is None:
                self.process_all_easyconfigs()

            dep_graph(fn, self.ordered_specs, silent=True)
    else:
        print "(skipped dep graph test)"

    def test_conflicts(self):
        """Check whether any conflicts occur in software dependency graphs."""
        if self.ordered_specs is None:
            self.process_all_easyconfigs()

        # construct a dictionary: (name, installver) tuple to dependencies
        depmap = {}
        for spec in self.ordered_specs:
            depmap.update({spec['module']: spec['unresolvedDependencies']})

        # iteratively expand list of dependencies until we reach the end (toolchain)
        depmap_last = None
        while depmap != depmap_last:
            depmap_last = copy.deepcopy(depmap)
            for (spec, dependencies) in depmap_last.items():
                for dep in dependencies:
                    depmap[spec].extend(depmap[dep])
                depmap[spec] = sorted(nub(depmap[spec]))

        # for each of the easyconfigs, check whether the dependencies contain any conflicts
        conflicts = False
        for ((name, installver), dependencies) in depmap.items():
            for (name_dep1, installver_dep1) in dependencies:
                for (name_dep2, installver_dep2) in dependencies:
                    # dependencies with the same name should have the exact same install version
                    # if not => CONFLICT!
                    # GHC is an exception, since it has a BUILD dependency on its own
                    if name_dep1 == name_dep2 and name_dep1 != 'GHC' and installver_dep1 != installver_dep2:
                        specname = '%s-%s' % (name, installver)
                        vs_msg = "%s-%s vs %s-%s" % (name_dep1, installver_dep1, name_dep2, installver_dep2)
                        print "Conflict found for dependencies of %s: %s" % (specname, vs_msg)
                        conflicts = True
        self.assertTrue(not conflicts, "No conflicts detected")


def template_easyconfig_test(self, spec):
    """Test whether all easyconfigs can be initialized."""

    f = open(spec, 'r')
    spectxt = f.read()
    f.close()

    # determine software name directly from easyconfig file
    res = self.name_regex.search(spectxt)
    if res:
        name = res.group(1)
    else:
        self.assertTrue(False, "Obtained software name directly from easyconfig file")

    # parse easyconfig 
    ec = EasyConfig(spec, validate=False)

    # sanity check for software name
    self.assertTrue(ec['name'], name) 

    # try and fetch easyblock spec from easyconfig
    easyblock = self.easyblock_regex.search(spectxt)
    if easyblock:
        easyblock = easyblock.group(1)

    # instantiate easyblock with easyconfig file
    app_class = get_class(easyblock, name=name)
    app = app_class(spec, validate_ec=False)

    # more sanity checks
    self.assertTrue(name, app.name)
    self.assertTrue(ec['version'], app.version)

    app.close_log()

def suite():
    """Return all easyblock initialisation tests."""

    # dynamically generate a separate test for each of the available easyblocks
    easyconfigs_path = get_paths_for("easyconfigs")[0]
    specs = glob.glob('%s/*/*/*.eb' % easyconfigs_path)

    for spec in specs:
        # dynamically define new inner functions that can be added as class methods to InitTest
        exec("def innertest(self): template_easyconfig_test(self, '%s')" % spec)
        spec = os.path.basename(spec)
        innertest.__doc__ = "Test for parsing of easyconfig %s" % spec
        innertest.__name__ = "test__parse_easyconfig_%s" % spec  # double underscore so parsing tests are run first
        setattr(EasyConfigTest, innertest.__name__, innertest)

    return TestLoader().loadTestsFromTestCase(EasyConfigTest)

if __name__ == '__main__':
    main()
