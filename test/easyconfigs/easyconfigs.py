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
import easybuild.tools.options as eboptions
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig.easyconfig import ActiveMNS, EasyConfig, fetch_parameter_from_easyconfig_file
from easybuild.framework.easyconfig.easyconfig import get_easyblock_class
from easybuild.framework.easyconfig.tools import dep_graph, get_paths_for, process_easyconfig, resolve_dependencies
from easybuild.tools import config
from easybuild.tools.module_naming_scheme import GENERAL_CLASS


# indicates whether all the single tests are OK,
# and that bigger tests (building dep graph, testing for conflicts, ...) can be run as well
# other than optimizing for time, this also helps to get around problems like http://bugs.python.org/issue10949
single_tests_ok = True

class EasyConfigTest(TestCase):
    """Baseclass for easyconfig testcases."""

    # initialize configuration (required for e.g. default modules_tool setting)
    eb_go = eboptions.parse_options()
    config.init(eb_go.options, eb_go.get_options_by_section('config'))
    build_options = {
        'check_osdeps': False,
        'force': True,
        'robot_path': get_paths_for("easyconfigs")[0],
        'suffix_modules_path': GENERAL_CLASS,
        'valid_module_classes': config.module_classes(),
        'valid_stops': [x[0] for x in EasyBlock.get_steps()],
    }
    config.init_build_options(build_options=build_options)
    config.set_tmpdir()
    del eb_go
        
    log = fancylogger.getLogger("EasyConfigTest", fname=False)
    # make sure a logger is present for main
    main._log = log
    ordered_specs = None
    parsed_easyconfigs = []

    def process_all_easyconfigs(self):
        """Process all easyconfigs and resolve inter-easyconfig dependencies."""
        # all available easyconfig files
        easyconfigs_path = get_paths_for("easyconfigs")[0]
        specs = glob.glob('%s/*/*/*.eb' % easyconfigs_path)

        # parse all easyconfigs if they haven't been already
        if not self.parsed_easyconfigs:
            for spec in specs:
                self.parsed_easyconfigs.extend(process_easyconfig(spec))

        self.ordered_specs = resolve_dependencies(self.parsed_easyconfigs)

    def test_dep_graph(self):
        """Unit test that builds a full dependency graph."""
        # pygraph dependencies required for constructing dependency graph are not available prior to Python 2.6
        if LooseVersion(sys.version) >= LooseVersion('2.6') and single_tests_ok:
            # temporary file for dep graph
            (hn, fn) = tempfile.mkstemp(suffix='.dot')
            os.close(hn)

            if self.ordered_specs is None:
                self.process_all_easyconfigs()

            dep_graph(fn, self.ordered_specs, silent=True)

            try:
                os.remove(fn)
            except OSError, err:
                log.error("Failed to remove %s: %s" % (fn, err))
        else:
            print "(skipped dep graph test)"

    def test_conflicts(self):
        """Check whether any conflicts occur in software dependency graphs."""

        if not single_tests_ok:
            print "(skipped conflicts test)"
            return

        if self.ordered_specs is None:
            self.process_all_easyconfigs()

        def mk_dep_mod_name(spec):
            return tuple(ActiveMNS().det_full_module_name(spec).split(os.path.sep))

        # construct a dictionary: (name, installver) tuple to dependencies
        depmap = {}
        for spec in self.ordered_specs:
            builddeps = map(mk_dep_mod_name, spec['builddependencies'])
            deps = map(mk_dep_mod_name, spec['unresolved_deps'])
            key = tuple(spec['full_mod_name'].split(os.path.sep))
            depmap.update({key: [builddeps, deps]})

        # iteratively expand list of (non-build) dependencies until we reach the end (toolchain)
        depmap_last = None
        while depmap != depmap_last:
            depmap_last = copy.deepcopy(depmap)
            for (spec, (builddependencies, dependencies)) in depmap_last.items():
                # extend dependencies with non-build dependencies of own (non-build) dependencies
                for dep in dependencies:
                    if dep not in builddependencies:
                        depmap[spec][1].extend([d for d in depmap[dep][1] if d not in depmap[dep][0]])
                depmap[spec][1] = sorted(nub(depmap[spec][1]))

        # for each of the easyconfigs, check whether the dependencies contain any conflicts
        conflicts = False
        for ((name, installver), (builddependencies, dependencies)) in depmap.items():
            # only consider non-build dependencies
            non_build_deps = [d for d in dependencies if d not in builddependencies]
            for i in xrange(len(non_build_deps)):
                (name_dep1, installver_dep1) = non_build_deps[i]
                # also make sure that module for easyconfig doesn't conflict with any of its dependencies
                for (name_dep2, installver_dep2) in [(name, installver)] + non_build_deps[i+1:]:
                    # dependencies with the same name should have the exact same install version
                    # if not => CONFLICT!
                    if name_dep1 == name_dep2 and installver_dep1 != installver_dep2:
                        specname = '%s-%s' % (name, installver)
                        vs_msg = "%s-%s vs %s-%s" % (name_dep1, installver_dep1, name_dep2, installver_dep2)
                        print "Conflict found for (non-build) dependencies of %s: %s" % (specname, vs_msg)
                        conflicts = True
        self.assertFalse(conflicts, "No conflicts detected")

    def test_easyconfig_locations(self):
        """Make sure all easyconfigs files are in the right location."""
        easyconfig_dirs_regex = re.compile(r'/easybuild/easyconfigs/[a-z]/[^/]+$')
        topdir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        for (dirpath, _, filenames) in os.walk(topdir):
            # ignore git/svn dirs
            if '/.git/' in dirpath or '/.svn/' in dirpath:
                continue
            # check whether list of .eb files is non-empty
            easyconfig_files = [fn for fn in filenames if fn.endswith('eb')]
            if easyconfig_files:
                # check whether path matches required pattern
                if not easyconfig_dirs_regex.search(dirpath):
                    # only exception: TEMPLATE.eb
                    if not (dirpath.endswith('/easybuild/easyconfigs') and filenames == ['TEMPLATE.eb']):
                        self.assertTrue(False, "List of easyconfig files in %s is empty: %s" % (dirpath, filenames))

def template_easyconfig_test(self, spec):
    """Test whether all easyconfigs can be initialized."""

    # set to False, so it's False in case of this test failing
    global single_tests_ok
    prev_single_tests_ok = single_tests_ok
    single_tests_ok = False

    # parse easyconfig 
    ecs = process_easyconfig(spec)
    if len(ecs) == 1:
        ec = ecs[0]['ec']
    else:
        self.assertTrue(False, "easyconfig %s does not contain blocks, yields only one parsed easyconfig" % spec)

    # sanity check for software name
    name = fetch_parameter_from_easyconfig_file(spec, 'name')
    self.assertTrue(ec['name'], name) 

    # try and fetch easyblock spec from easyconfig
    easyblock = fetch_parameter_from_easyconfig_file(spec, 'easyblock')

    # instantiate easyblock with easyconfig file
    app_class = get_easyblock_class(easyblock, name=name)
    app = app_class(ec)

    # more sanity checks
    self.assertTrue(name, app.name)
    self.assertTrue(ec['version'], app.version)

    # make sure all patch files are available
    specdir = os.path.dirname(spec)
    specfn = os.path.basename(spec)
    for patch in ec['patches']:
        if isinstance(patch, (tuple, list)):
            patch = patch[0]
        # only check actual patch files, not other files being copied via the patch functionality
        if patch.endswith('.patch'):
            patch_full = os.path.join(specdir, patch)
            msg = "Patch file %s is available for %s" % (patch_full, specfn)
            self.assertTrue(os.path.isfile(patch_full), msg)
    ext_patches = []
    for ext in ec['exts_list']:
        if isinstance(ext, (tuple, list)) and len(ext) == 3:
            self.assertTrue(isinstance(ext[2], dict), "3rd element of extension spec is a dictionary")
            for ext_patch in ext[2].get('patches', []):
                if isinstance(ext_patch, (tuple, list)):
                    ext_patch = ext_patch[0]
                # only check actual patch files, not other files being copied via the patch functionality
                if ext_patch.endswith('.patch'):
                    ext_patch_full = os.path.join(specdir, ext_patch)
                    msg = "Patch file %s is available for %s" % (ext_patch_full, specfn)
                    self.assertTrue(os.path.isfile(ext_patch_full), msg)

    app.close_log()
    os.remove(app.logfile)

    # cache the parsed easyconfig, to avoid that it is parsed again
    self.parsed_easyconfigs.append(ecs[0])

    # test passed, so set back to True
    single_tests_ok = True and prev_single_tests_ok

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
