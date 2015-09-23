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
import shutil
import sys
import tempfile
from distutils.version import LooseVersion
from vsc.utils import fancylogger
from vsc.utils.missing import nub
from unittest import TestCase, TestLoader, main

import easybuild.main as main
import easybuild.tools.options as eboptions
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig.easyconfig import EasyConfig
from easybuild.framework.easyconfig.easyconfig import get_easyblock_class
from easybuild.framework.easyconfig.parser import fetch_parameters_from_easyconfig
from easybuild.framework.easyconfig.tools import dep_graph, get_paths_for, process_easyconfig
from easybuild.tools import config
from easybuild.tools.filetools import write_file
from easybuild.tools.module_naming_scheme import GENERAL_CLASS
from easybuild.tools.module_naming_scheme.easybuild_mns import EasyBuildMNS
from easybuild.tools.module_naming_scheme.utilities import det_full_ec_version
from easybuild.tools.modules import modules_tool
from easybuild.tools.robot import resolve_dependencies


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
        'external_modules_metadata': {},
        'force': True,
        'optarch': 'test',
        'robot_path': get_paths_for("easyconfigs")[0],
        'silent': True,
        'suffix_modules_path': GENERAL_CLASS,
        'valid_module_classes': config.module_classes(),
        'valid_stops': [x[0] for x in EasyBlock.get_steps()],
    }
    config.init_build_options(build_options=build_options)
    config.set_tmpdir()
    del eb_go

    # put dummy 'craype-test' module in place, which is required for parsing easyconfigs using Cray* toolchains
    TMPDIR = tempfile.mkdtemp()
    os.environ['MODULEPATH'] = TMPDIR
    write_file(os.path.join(TMPDIR, 'craype-test'), '#%Module\n')

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

        # filter out external modules
        for ec in self.parsed_easyconfigs:
            for dep in ec['dependencies'][:]:
                if dep.get('external_module', False):
                    ec['dependencies'].remove(dep)

        self.ordered_specs = resolve_dependencies(self.parsed_easyconfigs, retain_all_deps=True)

    def test_dep_graph(self):
        """Unit test that builds a full dependency graph."""
        # pygraph dependencies required for constructing dependency graph are not available prior to Python 2.6
        if LooseVersion(sys.version) >= LooseVersion('2.6') and single_tests_ok:
            # temporary file for dep graph
            (hn, fn) = tempfile.mkstemp(suffix='.dot')
            os.close(hn)

            if self.ordered_specs is None:
                self.process_all_easyconfigs()

            dep_graph(fn, self.ordered_specs)

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
            return tuple(EasyBuildMNS().det_full_module_name(spec).split(os.path.sep))

        # construct a dictionary: (name, installver) tuple to (build) dependencies
        depmap = {}
        for spec in self.ordered_specs:
            # exclude external modules, since we can't check conflicts on them (we don't even know the software name)
            build_deps = [mk_dep_mod_name(d) for d in spec['builddependencies'] if not d.get('external_module', False)]
            deps = [mk_dep_mod_name(d) for d in spec['ec'].all_dependencies if not d.get('external_module', False)]

            # separate runtime deps from build deps
            runtime_deps = [d for d in deps if d not in build_deps]
            key = tuple(spec['full_mod_name'].split(os.path.sep))
            depmap.update({key: [build_deps, runtime_deps]})

        # iteratively expand list of dependencies
        depmap_last = None
        while depmap != depmap_last:
            depmap_last = copy.deepcopy(depmap)
            for (spec, (build_deps, runtime_deps)) in depmap_last.items():
                # extend runtime dependencies with non-build dependencies of own runtime dependencies
                for dep in runtime_deps:
                    depmap[spec][1].extend([d for d in depmap[dep][1] if d not in depmap[dep][0]])
                depmap[spec][1] = sorted(nub(depmap[spec][1]))
                # extend build dependencies with non-build dependencies of own build dependencies
                for dep in build_deps:
                    depmap[spec][0].extend([d for d in depmap[dep][1] if d not in depmap[dep][0]])
                depmap[spec][0] = sorted(nub(depmap[spec][0]))

        def check_conflict((name, installver), (name1, installver1), (name2, installver2)):
            """Check whether dependencies with given name/(install) version conflict with each other."""
            # dependencies with the same name should have the exact same install version
            # if not => CONFLICT!
            if name1 == name2 and installver1 != installver2:
                specname = '%s-%s' % (name, installver)
                vs_msg = "%s-%s vs %s-%s" % (name1, installver1, name2, installver2)
                print "Conflict found for dependencies of %s: %s" % (specname, vs_msg)
                return True
            else:
                return False

        # for each of the easyconfigs, check whether the dependencies (incl. build deps) contain any conflicts
        conflicts = False
        for ((name, installver), (build_deps, runtime_deps)) in depmap.items():
            # also check whether module itself clashes with any of its dependencies
            for i, dep1 in enumerate(build_deps + runtime_deps + [(name, installver)]):
                for dep2 in (build_deps + runtime_deps)[i+1:]:
                    # don't worry about conflicts between module itself and any of its build deps
                    if dep1 != (name, installver) or dep2 not in build_deps:
                        conflicts |= check_conflict((name, installver), dep1, dep2)
        self.assertFalse(conflicts, "No conflicts detected")

    def test_sanity_check_paths(self):
        """Make sure specified sanity check paths adher to the requirements."""

        if self.ordered_specs is None:
            self.process_all_easyconfigs()

        for ec in self.parsed_easyconfigs:
            ec_scp = ec['ec']['sanity_check_paths']
            if ec_scp != {}:
                # if sanity_check_paths is specified (i.e., non-default), it must adher to the requirements
                # both 'files' and 'dirs' keys, both with list values and with at least one a non-empty list
                error_msg = "sanity_check_paths for %s does not meet requirements: %s" % (ec['spec'], ec_scp)
                self.assertEqual(sorted(ec_scp.keys()), ['dirs', 'files'], error_msg)
                self.assertTrue(isinstance(ec_scp['dirs'], list), error_msg)
                self.assertTrue(isinstance(ec_scp['files'], list), error_msg)
                self.assertTrue(ec_scp['dirs'] or ec_scp['files'], error_msg)

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

    def test_zzz_cleanup(self):
        """Dummy test to clean up global temporary directory."""
        shutil.rmtree(self.TMPDIR)

def template_easyconfig_test(self, spec):
    """Tests for an individual easyconfig: parsing, instantiating easyblock, check patches, ..."""

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

    # check easyconfig file name
    expected_fn = '%s-%s.eb' % (ec['name'], det_full_ec_version(ec))
    msg = "Filename '%s' of parsed easyconfig matches expected filename '%s'" % (spec, expected_fn)
    self.assertEqual(os.path.basename(spec), expected_fn, msg)

    name, easyblock = fetch_parameters_from_easyconfig(ec.rawtxt, ['name', 'easyblock'])

    # sanity check for software name
    self.assertTrue(ec['name'], name)

    # instantiate easyblock with easyconfig file
    app_class = get_easyblock_class(easyblock, name=name)

    # check that automagic fallback to ConfigureMake isn't done (deprecated behaviour)
    fn = os.path.basename(spec)
    error_msg = "%s relies on automagic fallback to ConfigureMake, should use easyblock = 'ConfigureMake' instead" % fn
    self.assertTrue(easyblock or not app_class is ConfigureMake, error_msg)

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

    # check whether all extra_options defined for used easyblock are defined
    for key in app.extra_options():
        self.assertTrue(key in app.cfg)

    app.close_log()
    os.remove(app.logfile)

    # dump the easyconfig file
    handle, test_ecfile = tempfile.mkstemp()
    os.close(handle)

    ec.dump(test_ecfile)
    dumped_ec = EasyConfig(test_ecfile)
    os.remove(test_ecfile)

    # inject dummy values for templates that are only known at a later stage
    dummy_template_values = {
        'builddir': '/dummy/builddir',
        'installdir': '/dummy/installdir',
    }
    ec.template_values.update(dummy_template_values)
    dumped_ec.template_values.update(dummy_template_values)

    for key in sorted(ec._config):
        self.assertEqual(ec[key], dumped_ec[key])

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
