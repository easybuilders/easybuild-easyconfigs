##
# Copyright 2013-2025 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
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
Unit tests for easyconfig files.

@author: Kenneth Hoste (Ghent University)
"""
import glob
import os
import re
import shutil
import stat
import tempfile
from collections import defaultdict
from unittest import TestCase, TestLoader, main, skip
from urllib.request import Request, urlopen

import easybuild.main as eb_main
import easybuild.tools.options as eboptions
from easybuild.base import fancylogger
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.easyblocks.generic.pythonpackage import PythonPackage
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig.default import DEFAULT_CONFIG
from easybuild.framework.easyconfig.format.format import DEPENDENCY_PARAMETERS
from easybuild.framework.easyconfig.easyconfig import get_easyblock_class, letter_dir_for
from easybuild.framework.easyconfig.easyconfig import resolve_template
from easybuild.framework.easyconfig.parser import (
    EasyConfigParser, fetch_parameters_from_easyconfig,
    DEPRECATED_EASYCONFIG_PARAMETERS,
)
from easybuild.framework.easyconfig.tools import check_sha256_checksums, dep_graph, get_paths_for, process_easyconfig
from easybuild.tools import config, LooseVersion
from easybuild.tools.config import GENERAL_CLASS, build_option
from easybuild.tools.filetools import change_dir, is_generic_easyblock, read_file, remove_file
from easybuild.tools.filetools import verify_checksum, which, write_file
from easybuild.tools.module_naming_scheme.utilities import det_full_ec_version
from easybuild.tools.modules import modules_tool
from easybuild.tools.robot import check_conflicts, resolve_dependencies
from easybuild.tools.run import run_shell_cmd
from easybuild.tools.options import set_tmpdir
from easybuild.tools.utilities import nub


# indicates whether all the single tests are OK,
# and that bigger tests (building dep graph, testing for conflicts, ...) can be run as well
# other than optimizing for time, this also helps to get around problems like http://bugs.python.org/issue10949
single_tests_ok = True


def is_pr():
    """Return true if run in a pull request CI"""
    # $TRAVIS_PULL_REQUEST should be a PR number, otherwise we're not running tests for a PR
    travis_pr_test = re.match('^[0-9]+$', os.environ.get('TRAVIS_PULL_REQUEST', ''))

    # when testing a PR in GitHub Actions, $GITHUB_EVENT_NAME will be set to 'pull_request'
    github_pr_test = os.environ.get('GITHUB_EVENT_NAME') == 'pull_request'
    return travis_pr_test or github_pr_test


def get_target_branch():
    """Return the target branch of a pull request"""
    # target branch should be anything other than 'master';
    # usually is 'develop', but could also be a release branch like '3.7.x'
    target_branch = os.environ.get('GITHUB_BASE_REF', None)
    if not target_branch:
        target_branch = os.environ.get('TRAVIS_BRANCH', None)
    if not target_branch:
        raise RuntimeError("Did not find a target branch")
    return target_branch


def skip_if_not_pr_to_non_main_branch():
    if not is_pr():
        return skip("Only run for pull requests")
    if get_target_branch() == "main":
        return skip("Not run for pull requests against main")
    return lambda func: func


def get_files_from_diff(diff_filter, ext):
    """Return the files changed on HEAD relative to the current target branch"""
    target_branch = get_target_branch()

    # relocate to top-level directory of repository to run 'git diff' command
    top_dir = os.path.dirname(os.path.dirname(get_paths_for('easyconfigs')[0]))
    cwd = change_dir(top_dir)

    # first determine the 'merge base' between target branch and PR branch
    # cfr. https://git-scm.com/docs/git-merge-base
    cmd = "git merge-base %s HEAD" % target_branch
    res = run_shell_cmd(cmd, fail_on_error=False, hidden=True)
    if res.exit_code == 0:
        merge_base = res.output.strip()
        print("Merge base for %s and HEAD: %s" % (target_branch, merge_base))
    else:
        msg = "Failed to determine merge base (exit_code: %s, output: '%s'), "
        msg += "falling back to specifying target branch %s"
        print(msg % (res.exit_code, res.output, target_branch))
        merge_base = target_branch

    # determine list of changed files using 'git diff' and merge base determined above
    cmd = "git diff --name-only --diff-filter=%s %s..HEAD --" % (diff_filter, merge_base)
    res = run_shell_cmd(cmd, hidden=True)
    files = [os.path.join(top_dir, f) for f in res.output.strip().split('\n') if f.endswith(ext)]

    change_dir(cwd)
    return files


def get_eb_files_from_diff(diff_filter):
    """Return the easyconfig files changed on HEAD relative to the current target branch"""
    return get_files_from_diff(diff_filter, '.eb')


class EasyConfigTest(TestCase):
    """Baseclass for easyconfig testcases."""

    @classmethod
    def setUpClass(cls):
        """Setup environment for all tests. Called once!"""
        # make sure that the EasyBuild installation is still known even if we purge an EB module
        if os.getenv('EB_SCRIPT_PATH') is None:
            eb_path = which('eb')
            if eb_path is not None:
                os.environ['EB_SCRIPT_PATH'] = eb_path

        # initialize configuration (required for e.g. default modules_tool setting)
        eb_go = eboptions.parse_options(args=[])  # Ignore cmdline args as those are meant for the unittest framework
        config.init(eb_go.options, eb_go.get_options_by_section('config'))
        build_options = {
            'check_osdeps': False,
            'external_modules_metadata': {},
            'force': True,
            'local_var_naming_check': 'error',
            'optarch': 'test',
            'robot_path': get_paths_for("easyconfigs")[0],
            'silent': True,
            'suffix_modules_path': GENERAL_CLASS,
            'valid_module_classes': config.module_classes(),
            'valid_stops': [x[0] for x in EasyBlock.get_steps()],
        }
        config.init_build_options(build_options=build_options)
        set_tmpdir()

        # put dummy 'craype-test' module in place, which is required for parsing easyconfigs using Cray* toolchains
        cls.TMPDIR = tempfile.mkdtemp()
        os.environ['MODULEPATH'] = cls.TMPDIR
        write_file(os.path.join(cls.TMPDIR, 'craype-test'), '#%Module\n')

        log = fancylogger.getLogger("EasyConfigTest", fname=False)

        # make sure a logger is present for main
        eb_main._log = log

        cls._ordered_specs = None
        cls._parsed_easyconfigs = []
        cls._parsed_all_easyconfigs = False
        cls._changed_ecs = None  # easyconfigs changed in a PR
        cls._changed_patches = None  # patches changed in a PR

    @classmethod
    def tearDownClass(cls):
        """Cleanup after running all tests"""
        shutil.rmtree(cls.TMPDIR)

    @classmethod
    def parse_all_easyconfigs(cls):
        """Parse all easyconfigs."""
        if cls._parsed_all_easyconfigs:
            return
        # all available easyconfig files
        easyconfigs_path = get_paths_for("easyconfigs")[0]
        specs = glob.glob('%s/*/*/*.eb' % easyconfigs_path)
        parsed_specs = {ec['spec'] for ec in cls._parsed_easyconfigs}
        for spec in specs:
            if spec not in parsed_specs:
                cls._parsed_easyconfigs.extend(process_easyconfig(spec))
        cls._parsed_all_easyconfigs = True

    @classmethod
    def resolve_all_dependencies(cls):
        """Resolve dependencies between easyconfigs"""
        # Parse all easyconfigs if not done yet
        cls.parse_all_easyconfigs()
        # filter out external modules
        for ec in cls._parsed_easyconfigs:
            for dep in ec['dependencies'][:]:
                if dep.get('external_module', False):
                    ec['dependencies'].remove(dep)
        cls._ordered_specs = resolve_dependencies(
            cls._parsed_easyconfigs, modules_tool(), retain_all_deps=True)

    def _get_changed_easyconfigs(self):
        """Gather all added or modified easyconfigs"""
        # get list of changed easyconfigs
        changed_ecs_files = get_eb_files_from_diff(diff_filter='M')
        added_ecs_files = get_eb_files_from_diff(diff_filter='A')

        # ignore archived easyconfigs
        def filter_ecs(ecs):
            archive_path = os.path.join('easybuild', 'easyconfigs', '__archive__')
            return [ec for ec in ecs if archive_path not in ec]

        changed_ecs_files = filter_ecs(changed_ecs_files)
        added_ecs_files = filter_ecs(added_ecs_files)

        changed_ecs_filenames = [os.path.basename(f) for f in changed_ecs_files]
        added_ecs_filenames = [os.path.basename(f) for f in added_ecs_files]
        if changed_ecs_filenames:
            print("\nList of changed easyconfig files in this PR:\n\t%s" % '\n\t'.join(changed_ecs_filenames))
        if added_ecs_filenames:
            print("\nList of added easyconfig files in this PR:\n\t%s" % '\n\t'.join(added_ecs_filenames))
        EasyConfigTest._changed_ecs_filenames = changed_ecs_filenames
        EasyConfigTest._added_ecs_filenames = added_ecs_filenames

        # grab parsed easyconfigs for changed easyconfig files
        changed_ecs = []
        easyconfigs_path = get_paths_for("easyconfigs")[0]
        for ec_file in changed_ecs_files + added_ecs_files:
            # Search in already parsed ECs first
            match = next((ec['ec'] for ec in EasyConfigTest._parsed_easyconfigs if ec['spec'] == ec_file), None)

            if match:
                changed_ecs.append(match)
            elif ec_file.startswith(easyconfigs_path):
                ec = process_easyconfig(ec_file)
                # Cache non-archived files
                if '__archive__' not in ec_file:
                    EasyConfigTest._parsed_easyconfigs.extend(ec)
                changed_ecs.append(ec[0]['ec'])
            else:
                raise RuntimeError("Failed to find parsed easyconfig for %s" % os.path.basename(ec_file))
        EasyConfigTest._changed_ecs = changed_ecs

    def _get_changed_patches(self):
        """Gather all added or modified patches"""

        # get list of changed/added patch files
        changed_patches = get_files_from_diff(diff_filter='M', ext='.patch')
        added_patches = get_files_from_diff(diff_filter='A', ext='.patch')

        if changed_patches:
            print("\nList of changed patch files in this PR:\n\t%s" % '\n\t'.join(changed_patches))
        if added_patches:
            print("\nList of added patch files in this PR:\n\t%s" % '\n\t'.join(added_patches))

        EasyConfigTest._changed_patches = changed_patches + added_patches

    @property
    def parsed_easyconfigs(self):
        # parse all easyconfigs if they haven't been already
        EasyConfigTest.parse_all_easyconfigs()
        return EasyConfigTest._parsed_easyconfigs

    @property
    def ordered_specs(self):
        # Resolve dependencies if not done
        if EasyConfigTest._ordered_specs is None:
            EasyConfigTest.resolve_all_dependencies()
        return EasyConfigTest._ordered_specs

    @property
    def changed_ecs_filenames(self):
        if EasyConfigTest._changed_ecs is None:
            self._get_changed_easyconfigs()
        return EasyConfigTest._changed_ecs_filenames

    @property
    def added_ecs_filenames(self):
        if EasyConfigTest._changed_ecs is None:
            self._get_changed_easyconfigs()
        return EasyConfigTest._added_ecs_filenames

    @property
    def changed_ecs(self):
        if EasyConfigTest._changed_ecs is None:
            self._get_changed_easyconfigs()
        return EasyConfigTest._changed_ecs

    @property
    def changed_patches(self):
        if EasyConfigTest._changed_patches is None:
            self._get_changed_patches()
        return EasyConfigTest._changed_patches

    def test_dep_graph(self):
        """Unit test that builds a full dependency graph."""

        if not single_tests_ok:
            print("(skipped dep graph test)")
            return

        # temporary file for dep graph
        (hn, fn) = tempfile.mkstemp(suffix='.dot')
        os.close(hn)

        dep_graph(fn, self.ordered_specs)

        remove_file(fn)

    def test_conflicts(self):
        """Check whether any conflicts occur in software dependency graphs."""

        if not single_tests_ok:
            print("(skipped conflicts test)")
            return

        self.assertFalse(check_conflicts(self.ordered_specs, modules_tool(), check_inter_ec_conflicts=False),
                         "No conflicts detected")

    def test_deps(self):
        """Perform checks on dependencies in easyconfig files"""

        fails = []

        for ec in self.parsed_easyconfigs:
            # make sure we don't add backdoored XZ versions (5.6.0, 5.6.1)
            # see https://access.redhat.com/security/cve/CVE-2024-3094
            if ec['ec']['name'] == 'XZ' and ec['ec']['version'] in ('5.6.0', '5.6.1'):
                fail = ("XZ versions 5.6.0 and 5.6.1 contain malicious code, and should not be introduced into"
                        " EasyBuild. Please use another version instead. For more details, see"
                        " https://access.redhat.com/security/cve/CVE-2024-3094")
                fails.append(fail)

            # make sure that no odd versions (like 1.13) of HDF5 are used as a dependency,
            # since those are released candidates - only even versions (like 1.12) are stable releases;
            # see https://docs.hdfgroup.org/archive/support/HDF5/doc/TechNotes/Version.html
            for dep in ec['ec'].dependencies():
                if dep['name'] == 'HDF5':
                    ver = dep['version']
                    if int(ver.split('.')[1]) % 2 == 1:
                        fail = "Odd minor versions of HDF5 should not be used as a dependency: "
                        fail += "found HDF5 v%s as dependency in %s" % (ver, os.path.basename(ec['spec']))
                        fails.append(fail)

        self.assertFalse(len(fails), '\n'.join(sorted(fails)))

    def check_dep_vars(self, gen, dep, dep_vars):
        """Check whether available variants of a particular dependency are acceptable or not."""

        # short-circuit in case there's only one dependency variant, or none at all
        if len(dep_vars) <= 1:
            return True

        # 'guilty' until proven 'innocent'
        res = False

        # filter out wrapped Java or dotNET-Core versions
        # i.e. if the version of one is a prefix of the version of the other one (e.g. 1.8 & 1.8.0_181)
        if dep in ['Java', 'dotNET-Core']:
            dep_vars_to_check = sorted(dep_vars.keys())

            retained_dep_vars = []

            while dep_vars_to_check:
                dep_var = dep_vars_to_check.pop()
                dep_var_version = dep_var.split(';')[0]

                # remove dep vars wrapped by current dep var
                dep_vars_to_check = [x for x in dep_vars_to_check if not x.startswith(dep_var_version + '.')]

                retained_dep_vars = [x for x in retained_dep_vars if not x.startswith(dep_var_version + '.')]

                retained_dep_vars.append(dep_var)

            for key in list(dep_vars.keys()):
                if key not in retained_dep_vars:
                    del dep_vars[key]

        version_regex = re.compile('^version: (?P<version>[^;]+);')

        # multiple variants of HTSlib is OK as long as they are deps for a matching version of BCFtools;
        # same goes for WRF and WPS; Gurobi and Rgurobi; ncbi-vdb and SRA-Toolkit
        multiple_allowed_variants = [('HTSlib', 'BCFtools'),
                                     ('WRF', 'WPS'),
                                     ('Gurobi', 'Rgurobi'),
                                     ('ncbi-vdb', 'SRA-Toolkit')]
        for dep_name, parent_name in multiple_allowed_variants:
            if dep == dep_name and len(dep_vars) > 1:
                for key in list(dep_vars):
                    ecs = dep_vars[key]
                    # filter out dep variants that are only used as dependency for parent with same version
                    dep_ver = version_regex.search(key).group('version')
                    if all(ec.startswith('%s-%s-' % (parent_name, dep_ver)) for ec in ecs) and len(dep_vars) > 1:
                        dep_vars.pop(key)

        # multiple variants of Meson is OK as long as they are deps for meson-python, since meson-python should only be
        # a build dependency elsewhere
        if dep == 'Meson' and len(dep_vars) > 1:
            for key in list(dep_vars):
                ecs = dep_vars[key]
                # filter out Meson variants that are only used as a dependency for meson-python
                if all(ec.startswith('meson-python-') for ec in ecs):
                    dep_vars.pop(key)
                # always retain at least one dep variant
                if len(dep_vars) == 1:
                    break

        # multiple versions of Boost is OK as long as they are deps for a matching Boost.Python
        if dep == 'Boost' and len(dep_vars) > 1:
            for key in list(dep_vars):
                ecs = dep_vars[key]
                # filter out Boost variants that are only used as dependency for Boost.Python with same version
                boost_ver = version_regex.search(key).group('version')
                if all(ec.startswith('Boost.Python-%s-' % boost_ver) for ec in ecs):
                    dep_vars.pop(key)

        # multiple variants of GPAW-setups is OK as long as they are deps for GPAW
        if dep == 'GPAW-setups' and len(dep_vars) > 1:
            for key in list(dep_vars):
                ecs = dep_vars[key]
                # filter out GPAW-setups variants that are only used as a dependency for GPAW
                if all(ec.startswith('GPAW') for ec in ecs):
                    dep_vars.pop(key)
                # always retain at least one dep variant
                if len(dep_vars) == 1:
                    break

        # Pairs of name, versionsuffix that should be removed from dep_vars if exactly one matching key is found.
        # The name is checked against 'dep' and can be a list to allow multiple
        # If the versionsuffix is a 2-element tuple, the second element should be set to True
        # to interpret the first element as the start of the suffix (e.g. to include trailing version numbers)
        # Otherwise the whole versionsuffix must match for the filter to apply.
        filter_variants = [
            # filter out binutils with empty versionsuffix which is used to build toolchain compiler
            ('binutils', ''),
            # filter out Perl with -minimal versionsuffix which are only used in makeinfo-minimal
            ('Perl', '-minimal'),
            # filter out FFTW and imkl with -serial versionsuffix which are used in non-MPI subtoolchains
            # Same for HDF5 with -serial versionsuffix which is used in HDF5 for Python (h5py)
            (['FFTW', 'imkl', 'HDF5'], '-serial'),
            # filter out BLIS and libFLAME with -amd versionsuffix
            # (AMD forks, used in gobff/*-amd toolchains)
            (['BLIS', 'libFLAME'], '-amd'),
            # filter out libcint with -pypzpx versionsuffix, used by MOLGW
            ('libcint', '-pypzpx'),
            # filter out OpenBLAS with -int8 versionsuffix, used by GAMESS-US
            ('OpenBLAS', '-int8'),
            # filter out ScaLAPACK with -BLIS-* versionsuffix, used in goblf toolchain
            ('ScaLAPACK', ('-BLIS-', True)),
            # filter out ScaLAPACK with -bf versionsuffix, used in gobff toolchain
            ('ScaLAPACK', '-bf'),
            # filter out ScaLAPACK with -bl versionsuffix, used in goblf toolchain
            ('ScaLAPACK', '-bl'),
            # filter out ELSI variants with -PEXSI suffix
            ('ELSI', '-PEXSI'),
            # For Z3 the EC including Python bindings has a matching versionsuffix
            # filter out one per Python version
            ('Z3', ('-Python-2', True)),
            ('Z3', ('-Python-3', True)),
            # allow Graphviz coexistence by ignoring the -minimal variant when both exist
            ('Graphviz', '-minimal'),
        ]
        for dep_name, version_suffix in filter_variants:
            # always retain at least one dep variant
            if len(dep_vars) == 1:
                break
            if isinstance(dep_name, str):
                if dep != dep_name:
                    continue
            elif dep not in dep_name:
                continue
            if isinstance(version_suffix, str):
                match_prefix = False
            else:
                version_suffix, match_prefix = version_suffix
            search = 'versionsuffix: ' + version_suffix
            if match_prefix:
                matches = [v for v in dep_vars if search in v]
            else:
                matches = [v for v in dep_vars if v.endswith(search)]
            if len(matches) == 1:
                del dep_vars[matches[0]]

        # for some dependencies, we allow exceptions for software that depends on a particular version,
        # as long as that's indicated by the versionsuffix
        versionsuffix_deps = ['ASE', 'Boost', 'CUDA', 'CUDAcore', 'Java', 'Lua',
                              'PLUMED', 'PyTorch', 'R', 'Rust', 'TensorFlow']
        if dep in versionsuffix_deps and len(dep_vars) > 1:

            # check for '-CUDA-*' versionsuffix for CUDAcore dependency
            if dep == 'CUDAcore':
                dep = 'CUDA'

            for key in list(dep_vars):
                dep_ver = version_regex.search(key).group('version')
                # use version of Java wrapper rather than full Java version
                if dep == 'Java':
                    dep_ver = '.'.join(dep_ver.split('.')[:2])
                # filter out dep version if all easyconfig filenames using it include specific dep version
                if all(re.search('-%s-%s' % (dep, dep_ver), v) for v in dep_vars[key]):
                    dep_vars.pop(key)
                # always retain at least one dep variant
                if len(dep_vars) == 1:
                    break

            # filter R dep for a specific version of Python 2.x
            if dep == 'R' and len(dep_vars) > 1:
                for key in list(dep_vars):
                    if '; versionsuffix: -Python-2' in key:
                        dep_vars.pop(key)
                    # always retain at least one variant
                    if len(dep_vars) == 1:
                        break

        # for some dependencies, we allow exceptions for software with the same version
        # but with a -int64 versionsuffix in both the dependency and all its dependents
        int64_deps = ['SCOTCH', 'METIS']
        if dep in int64_deps and len(dep_vars) > 1:
            unique_dep_vers = {version_regex.search(x).group('version') for x in list(dep_vars)}
            if len(unique_dep_vers) == 1:
                for key in list(dep_vars):
                    if all(re.search('-int64', v) for v in dep_vars[key]) and re.search(
                        '; versionsuffix: .*-int64', key
                    ):
                        dep_vars.pop(key)
                    # always retain at least one dep variant
                    if len(dep_vars) == 1:
                        break

        # filter out variants that are specific to a particular version of CUDA
        cuda_dep_vars = [v for v in dep_vars.keys() if '-CUDA' in v]
        if len(dep_vars) >= len(cuda_dep_vars) and len(dep_vars) > 1:
            for key in list(dep_vars):
                if re.search('; versionsuffix: .*-CUDA-[0-9.]+', key):
                    dep_vars.pop(key)
                    # always retain at least one dep variant
                    if len(dep_vars) == 1:
                        break

        # some software packages require a specific (older/newer) version of a particular dependency
        alt_dep_versions = {
            # scanpy-1.10.4 and scvi-tools-1.4.1 requires anndata >= 0.11
            'aiida-core': [(r'2\.7\.2', [r'aiida-shell-', r'AITW-viscosity-'])],
            'anndata': [(r'0\.11\.4', [r'scvi-tools-1.4.1-', r'scanpy-1.10.4-'])],
            # arrow-R 6.0.0.2 is used for two R/R-bundle-Bioconductor sets (4.1.2/3.14 and 4.2.0/3.15)
            'arrow-R': [('6.0.0.2', [r'R-bundle-Bioconductor-'])],
            # BRAKER 3.0.8 depends on AUGUSTUS 3.5.0-20240612
            'AUGUSTUS': [(r'3\.5\.0-20240612', [r'BRAKER-3\.0\.8'])],
            # HOOMD-blue v4.9.1 requires Clang 16.x built with the shared libLLVM.so library
            'Clang': [(r'16\.0\.6; versionsuffix: -shared', [r'HOOMD-blue-4\.9\.1-foss-2023a-llvm'])],
            # GATE 9.2 requires CHLEP 2.4.5.1 and Geant4 11.0.x
            'CLHEP': [('2.4.5.1;', [r'GATE-9\.2-foss-2021b'])],
            # Score-P 8.3+ requires Cube 4.8.2+ but we have 4.8.1 already
            'CubeLib': [(r'4\.8\.2;', [r'Score-P-8\.[3-9]'])],
            'CubeWriter': [(r'4\.8\.2;', [r'Score-P-8\.[3-9]'])],
            # MACE-0.3.8-CUDA-12.1.1 needs e3nn-0.4.4-CUDA-12.1.1 as dependency
            'e3nn': [(r'0\.4\.4; versionsuffix: -CUDA-12\.1\.1', [r'MACE-0\.3\.8-foss-2023a-CUDA-12\.1\.1'])],
            # Current rapthor requires WSclean 3.5 or newer, which in turn requires EveryBeam 0.6.X or newer
            # Requires us to also bump DP3 version (to 6.2) and its dependency on EveryBeam
            'EveryBeam': [(r'0\.6\.1', [r'DP3-6\.2',
                                        r'WSClean-3\.[5-9]',
                                        r'LSMTool-1.7.0-foss-2023b',
                                        r'LINC-5.0-foss-2023b'])],
            # egl variant of glew is required by libwpe, wpebackend-fdo + WebKitGTK+ depend on libwpe
            'glew': [
                ('2.2.0; versionsuffix: -egl', [r'libwpe-1\.13\.3-GCCcore-11\.2\.0',
                                                r'libwpe-1\.14\.1-GCCcore-11\.3\.0',
                                                r'wpebackend-fdo-1\.13\.1-GCCcore-11\.2\.0',
                                                r'wpebackend-fdo-1\.14\.1-GCCcore-11\.3\.0',
                                                r'WebKitGTK\+-2\.37\.1-GCC-11\.2\.0',
                                                r'wxPython-4\.2\.0',
                                                r'wxPython-4\.2\.1',
                                                r'GRASS-8\.2\.0',
                                                r'QGIS-3\.28\.1']),
            ],
            # GATE 9.2 requires CHLEP 2.4.5.1 and Geant4 11.0.x
            'Geant4': [('11.0.1;', [r'GATE-9\.2-foss-2021b'])],
            # autoCAS requires serial h5py
            'h5py': [(r'3\.9\.0; versionsuffix: -serial', [r'autoCAS'])],
            # jax 0.2.24 is used as dep for AlphaFold 2.1.2 (other easyconfigs with foss/2021a use jax 0.3.9)
            'jax': [(r'0\.2\.24', [r'AlphaFold-2\.1\.2-foss-2021a'])],
            # Java 21 is used as dep for Octave 9.2.0, MDSplus 7.1 and JPype 1.5.0
            # (other 2023b easyconfigs use Java 11)
            'Java': [(r'21', [r'Octave-9\.2\.0', r'MDSplus-7\.1', r'JPype-1\.5\.0'])],
            # libxc 4.x is required by libGridXC
            # (Qiskit depends on PySCF), Elk 7.x requires libxc >= 5
            'libxc': [
                (r'4\.', [r'libGridXC-']),
                (r'5\.', [r'Elk-']),
            ],
            # OpenQP requires mpi4py>=4.0.0
            'mpi4py': [(r'4\.0\.1', [r'OpenQP-1\.0'])],
            # FDMNES requires sequential variant of MUMPS
            'MUMPS': [(r'5\.6\.1; versionsuffix: -metis-seq', [r'FDMNES'])],
            # RELION 5.0.0 requires fixes only in napari 0.4.19 and newer
            'napari': [(r'0\.4\.19\.post1;', [r'RELION-5\.0\.0'])],
            # SRA-toolkit 3.0.0 requires ncbi-vdb 3.0.0, Finder requires SRA-Toolkit 3.0.0
            'ncbi-vdb': [(r'3\.0\.0', [r'SRA-Toolkit-3\.0\.0', r'finder-1\.1\.0'])],
            'OpenFOAM': [
                # CFDEMcoupling requires OpenFOAM 5.x
                (r'5\.0-20180606', [r'CFDEMcoupling-3\.8\.0']),
            ],
            'ParaView': [
                # OpenFOAM 5.0 requires older ParaView, CFDEMcoupling depends on OpenFOAM 5.0
                (r'5\.4\.1', [r'CFDEMcoupling-3\.8\.0', r'OpenFOAM-5\.0-20180606']),
            ],
            'plumpy': [(r'0\.25\.0', [r'aiida-core-', r'aiida-shell-', r'AITW-viscosity-'])],
            'PMIx': [
                # PRRTE 4.0+ requires PMIx 6.0+ and vice-versa
                (r'6\.0\.0', [r'PRRTE-4\.0\.0']),
            ],
            'pydantic': [
                # GTDB-Tk v2.3.2 requires pydantic 1.x (see https://github.com/Ecogenomics/GTDBTk/pull/530)
                ('1.10.13;', ['GTDB-Tk-2.3.2-', 'GTDB-Tk-2.4.0-']),
            ],
            # Pydot <3 is explicitely required by cwltool
            'pydot': [(r'2\.0\.0', [r'LINC-5.0-foss-2023b',
                                    r'toil-cwl-8.2.0-foss-2023b',
                                    r'cwltool-3.1.20250110105449-foss-2023b'])],
            # bakta requires PyHMMER 0.10.15
            'PyHMMER': [(r'0\.10\.15', [r'bakta-1\.10\.1'])],
            # WhatsHap 1.4 + medaka 1.6.0 require Pysam >= 0.18.0 (NGSpeciesID depends on medaka)
            'Pysam': [
                ('0.18.0;', ['medaka-1.6.0-', 'NGSpeciesID-0.1.2.1-', 'WhatsHap-1.4-']),
            ],
            # bakta requires python-isal 1.6.1
            'python-isal': [(r'1\.6\.1', [r'bakta-1\.10\.1'])],
            # PyTorch-Lightning-1.8.4 is requiered in synthcity-0.2.10 and DECAF-synthetic-data-0.1.6
            'PyTorch-Lightning': [('1.8.4;', ['synthcity-0.2.10-', 'DECAF-synthetic-data-0.1.6-'])],
            # OPERA requires SAMtools 0.x
            'SAMtools': [(r'0\.', [r'ChimPipe-0\.9\.5', r'Cufflinks-2\.2\.1', r'OPERA-2\.0\.6',
                                   r'CGmapTools-0\.1\.2', r'BatMeth2-2\.1', r'OPERA-MS-0\.9\.0-20240703'])],
            # Ceres-Solver-2.2.0 needs SuiteSparse-7.8.2-METIS-5.1.0 from the used toolchain version
            'SuiteSparse': [(r'7\.8\.2; versionsuffix: -METIS-5.1.0', [r'Ceres-Solver-2\.2\.0-foss-2024a'])],
            # CheckM2 and its dep LightGBM requires scikit-learn-1.6.1
            'scikit-learn': [(r'1\.6\.1', [r'CheckM2-1\.1\.0-', r'LightGBM-4\.6\.0-'])],
            # UShER requires tbb-2020.3 as newer versions will not build
            # orthagogue requires tbb-2020.3 as 2021 versions are not backward compatible with the previous releases
            'tbb': [('2020.3', ['UShER-0.5.0-', 'orthAgogue-20141105-'])],
            'TensorFlow': [
                # medaka 1.5.0 (foss/2021a) depends on TensorFlow >=2.5.2, <2.6.0
                ('2.5.3;', ['medaka-1.5.0-']),
                # tensorflow-probability version to TF version
                ('2.8.4;', ['tensorflow-probability-0.16.0-']),
                # TensorFlow 2.15.1 is used by Clair3 v1.0.8 and tensorflow-probability 0.23.0
                ('2.15.1;', ['Clair3-1.0.8-', 'tensorflow-probability-0.23.0-']),
            ],
            # vLLM has pinned dependency tiktoken == 0.6.0
            'tiktoken': [('0.6.0;', ['vLLM-0.4.0-'])],
            # Transformers 4.57.1 needs tokenizers 0.22.1
            'tokenizers': [('0.22.1;', ['Transformers-4.57.1-'])],
            # smooth-topk uses a newer version of torchvision
            'torchvision': [('0.11.3;', ['smooth-topk-1.0-20210817-'])],
            # for the sake of backwards compatibility, keep UCX-CUDA v1.11.0 which depends on UCX v1.11.0
            # (for 2021b, UCX was updated to v1.11.2)
            'UCX': [('1.11.0;', ['UCX-CUDA-1.11.0-'])],
            # Napari 0.4.19post1 requires VisPy >=0.14.1 <0.15
            'VisPy': [('0.14.1;', ['napari-0.4.19.post1-', r'RELION-5\.0\.0'])],
            # Visit-3.4.1 requires VTK 9.2.x
            'VTK': [('9.2.6;', ['Visit-3.4.1-'])],
            # wxPython 4.2.0 depends on wxWidgets 3.2.0
            'wxWidgets': [(r'3\.2\.0', [r'wxPython-4\.2\.0', r'GRASS-8\.2\.0', r'QGIS-3\.28\.1'])],
        }
        if dep in alt_dep_versions and len(dep_vars) > 1:
            for key in list(dep_vars):
                for version_pattern, parents in alt_dep_versions[dep]:
                    # filter out known alternative dependency versions
                    if re.search('^version: %s' % version_pattern, key):
                        # only filter if the easyconfig using this dep variants is known
                        if all(any(re.search(p, x) for p in parents) for x in dep_vars[key]):
                            dep_vars.pop(key)

        # only single variant is always OK
        if len(dep_vars) == 1:
            res = True

        elif len(dep_vars) == 2 and dep in ['Python', 'Tkinter']:
            # for Python & Tkinter, it's OK to have on 2.x and one 3.x version
            v2_dep_vars = [x for x in dep_vars.keys() if x.startswith('version: 2.')]
            v3_dep_vars = [x for x in dep_vars.keys() if x.startswith('version: 3.')]
            if len(v2_dep_vars) == 1 and len(v3_dep_vars) == 1:
                res = True

        # two variants is OK if one is for Python 2.x and the other is for Python 3.x
        elif len(dep_vars) == 2:
            # there's no versionsuffix anymore for Python 3, but we still allow variants depending on Python 2.x + 3.x
            py2_dep_vars = [x for x in dep_vars.keys() if '; versionsuffix: -Python-2.' in x]
            py3_dep_vars = [x for x in dep_vars.keys() if x.strip().endswith('; versionsuffix:')]
            if len(py2_dep_vars) == 1 and len(py3_dep_vars) == 1:
                res = True

        return res

    def test_check_dep_vars(self):
        """Test check_dep_vars utility method."""

        # one single dep version: OK
        self.assertTrue(self.check_dep_vars('2019b', 'testdep', {
            'version: 1.2.3; versionsuffix:': ['foo-1.2.3.eb', 'bar-4.5.6.eb'],
        }))
        self.assertTrue(self.check_dep_vars('2019b', 'testdep', {
            'version: 1.2.3; versionsuffix: -test': ['foo-1.2.3.eb', 'bar-4.5.6.eb'],
        }))

        # two or more dep versions (no special case: not OK)
        self.assertFalse(self.check_dep_vars('2019b', 'testdep', {
            'version: 1.2.3; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 4.5.6; versionsuffix:': ['bar-4.5.6.eb'],
        }))
        self.assertFalse(self.check_dep_vars('2019b', 'testdep', {
            'version: 0.0; versionsuffix:': ['foobar-0.0.eb'],
            'version: 1.2.3; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 4.5.6; versionsuffix:': ['bar-4.5.6.eb'],
        }))

        # Java is a special case, with wrapped Java versions
        self.assertTrue(self.check_dep_vars('2019b', 'Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
        }))
        # two Java wrappers is not OK
        self.assertFalse(self.check_dep_vars('2019b', 'Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11.0.2; versionsuffix:': ['bar-4.5.6.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6.eb'],
        }))
        # OK to have two or more wrappers if versionsuffix is used to indicate exception
        self.assertTrue(self.check_dep_vars('2019b', 'Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11.0.2; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
        }))
        # versionsuffix must be there for all easyconfigs to indicate exception
        self.assertFalse(self.check_dep_vars('2019b', 'Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11.0.2; versionsuffix:': ['bar-4.5.6-Java-11.eb', 'bar-4.5.6.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6-Java-11.eb', 'bar-4.5.6.eb'],
        }))
        self.assertTrue(self.check_dep_vars('2019b', 'Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11.0.2; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
            'version: 12.1.6; versionsuffix:': ['foobar-0.0-Java-12.eb'],
            'version: 12; versionsuffix:': ['foobar-0.0-Java-12.eb'],
        }))

        # strange situation: odd number of Java versions
        # not OK: two Java wrappers (and no versionsuffix to indicate exception)
        self.assertFalse(self.check_dep_vars('2019b', 'Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6.eb'],
        }))
        # OK because of -Java-11 versionsuffix
        self.assertTrue(self.check_dep_vars('2019b', 'Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
        }))
        # not OK: two Java wrappers (and no versionsuffix to indicate exception)
        self.assertFalse(self.check_dep_vars('2019b', 'Java', {
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11.0.2; versionsuffix:': ['bar-4.5.6.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6.eb'],
        }))
        # OK because of -Java-11 versionsuffix
        self.assertTrue(self.check_dep_vars('2019b', 'Java', {
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11.0.2; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
        }))

        # two different versions of Boost is not OK
        self.assertFalse(self.check_dep_vars('2019b', 'Boost', {
            'version: 1.64.0; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.70.0; versionsuffix:': ['foo-2.3.4.eb'],
        }))

        # a different Boost version that is only used as dependency for a matching Boost.Python is fine
        self.assertTrue(self.check_dep_vars('2019a', 'Boost', {
            'version: 1.64.0; versionsuffix:': ['Boost.Python-1.64.0-gompi-2019a.eb'],
            'version: 1.70.0; versionsuffix:': ['foo-2.3.4.eb'],
        }))
        self.assertTrue(self.check_dep_vars('2019a', 'Boost', {
            'version: 1.64.0; versionsuffix:': ['Boost.Python-1.64.0-gompi-2019a.eb'],
            'version: 1.66.0; versionsuffix:': ['Boost.Python-1.66.0-gompi-2019a.eb'],
            'version: 1.70.0; versionsuffix:': ['foo-2.3.4.eb'],
        }))
        self.assertFalse(self.check_dep_vars('2019a', 'Boost', {
            'version: 1.64.0; versionsuffix:': ['Boost.Python-1.64.0-gompi-2019a.eb'],
            'version: 1.66.0; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.70.0; versionsuffix:': ['foo-2.3.4.eb'],
        }))

        self.assertTrue(self.check_dep_vars('2018a', 'Boost', {
            'version: 1.63.0; versionsuffix: -Python-2.7.14': ['EMAN2-2.21a-foss-2018a-Python-2.7.14-Boost-1.63.0.eb'],
            'version: 1.64.0; versionsuffix:': ['Boost.Python-1.64.0-gompi-2018a.eb'],
            'version: 1.66.0; versionsuffix:': ['BLAST+-2.7.1-foss-2018a.eb'],
        }))

        # two variants is OK, if they're for Python 2.x and 3.x, there's no versionsuffix anymore for Python 3
        self.assertTrue(self.check_dep_vars('2020b', 'Python', {
            'version: 2.7.18; versionsuffix:': ['SciPy-bundle-2020.11-foss-2020b-Python-2.7.18.eb'],
            'version: 3.8.6; versionsuffix:': ['SciPy-bundle-2020.11-foss-2020b.eb'],
        }))

        self.assertTrue(self.check_dep_vars('GCCcore-10.2', 'PyYAML', {
            'version: 5.3.1; versionsuffix:': ['IPython-7.18.1-GCCcore-10.2.0.eb'],
            'version: 5.3.1; versionsuffix: -Python-2.7.18': ['IPython-7.18.1-GCCcore-10.2.0-Python-2.7.18.eb'],
        }))

        self.assertTrue(self.check_dep_vars('2020b', 'SciPy-bundle', {
            'version: 2020.11; versionsuffix: -Python-2.7.18': ['matplotlib-3.3.3-foss-2020b-Python-2.7.18.eb'],
            'version: 2020.11; versionsuffix:': ['matplotlib-3.3.3-foss-2020b.eb'],
        }))

        # multiple dependency variants of specific software is OK, but only if indicated via versionsuffix
        self.assertTrue(self.check_dep_vars('2019b', 'TensorFlow', {
            'version: 1.15.2; versionsuffix: -TensorFlow-1.15.2':
                ['Horovod-0.18.2-fosscuda-2019b-TensorFlow-1.15.2.eb'],
            'version: 2.2.0; versionsuffix: -TensorFlow-2.2.0-Python-3.7.4':
                ['Horovod-0.19.5-fosscuda-2019b-TensorFlow-2.2.0-Python-3.7.4.eb'],
            'version: 2.1.0; versionsuffix: -Python-3.7.4': ['Keras-2.3.1-foss-2019b-Python-3.7.4.eb'],
        }))

        self.assertFalse(self.check_dep_vars('2019b', 'TensorFlow', {
            'version: 1.15.2; versionsuffix: ': ['Horovod-0.18.2-fosscuda-2019b.eb'],
            'version: 2.1.0; versionsuffix: -Python-3.7.4': ['Keras-2.3.1-foss-2019b-Python-3.7.4.eb'],
        }))

        self.assertTrue(self.check_dep_vars('2022b', 'Rust', {
            'version: 1.65.0; versionsuffix: ': ['maturin-1.1.0-GCCcore-12.2.0.eb'],
            'version: 1.75.0; versionsuffix: -Rust-1.75.0': ['maturin-1.4.0-GCCcore-12.2.0-Rust-1.75.0.eb'],
        }))

        self.assertFalse(self.check_dep_vars('2022b', 'Rust', {
            'version: 1.65.0; versionsuffix: ': ['maturin-1.1.0-GCCcore-12.2.0.eb'],
            'version: 1.75.0; versionsuffix: ': ['maturin-1.4.0-GCCcore-12.2.0.eb'],
        }))

    # some software also follows <year>{a,b} versioning scheme,
    # which throws off the pattern matching done below for toolchain versions
    multideps_false_positives_regex = re.compile(r'^MATLAB(-Engine)?-20[0-9][0-9][ab]')

    def test_dep_versions_per_toolchain(self):
        """
        Check whether there's only one dependency version per toolchain actively used.
        This is enforced to try and limit the chance of running into conflicts when multiple modules built with
        the same toolchain are loaded together.
        Generations 2023b and newer (GCC 13.2 and newer) are checked in the more stringent
        test_dep_versions_per_toolchain_generation.
        """
        ecs_by_full_mod_name = {ec['full_mod_name']: ec for ec in self.parsed_easyconfigs}
        if len(ecs_by_full_mod_name) != len(self.parsed_easyconfigs):
            self.fail('Easyconfigs with duplicate full_mod_name found')

        # Cache already determined dependencies
        ec_to_deps = {}

        def get_deps_for(ec):
            """Get list of (direct) dependencies for specified easyconfig."""
            ec_mod_name = ec['full_mod_name']
            deps = ec_to_deps.get(ec_mod_name)
            if deps is None:
                deps = []
                for dep in ec['ec']['dependencies']:
                    dep_mod_name = dep['full_mod_name']
                    deps.append((dep['name'], dep['version'], dep['versionsuffix'], dep_mod_name))
                    # Note: Raises KeyError if dep not found
                    res = ecs_by_full_mod_name[dep_mod_name]
                    deps.extend(get_deps_for(res))
                ec_to_deps[ec_mod_name] = deps
            return deps

        multi_dep_vars_msg = ''
        # restrict to checking dependencies of easyconfigs using common toolchains
        # and GCCcore subtoolchain for common toolchains
        patterns = [
            # compiler-only subtoolchains GCCcore, this pattern has never checked GCC toolchains
            # retain the check as it has always been in the old generation check
            r'GCCcore-1(0\.3|[12]\.[0-9])',  # GCCcore 10.3 to 12.3
            # intel-compilers
            r'intel-compilers-202([0-2]\.[0-9]|3\.[01])',  # intel-compilers up to 2023.1
            # full toolchains, like foss/2021a or intel/2022b
            r'202([12][ab]|3a)',  # 2021a to 2023a
        ]
        for pattern in patterns:
            all_deps = {}
            regex = re.compile(r'^.*-(?P<tc_gen>%s).*\.eb$' % pattern)

            # collect variants for all dependencies of easyconfigs that use a toolchain that matches
            for ec in self.ordered_specs:
                ec_file = os.path.basename(ec['spec'])

                # take into account software which also follows a <year>{a,b} versioning scheme
                ec_file = self.multideps_false_positives_regex.sub('', ec_file)

                res = regex.match(ec_file)
                if res:
                    tc_gen = res.group('tc_gen')
                    all_deps_tc_gen = all_deps.setdefault(tc_gen, {})
                    for dep_name, dep_ver, dep_versuff, dep_mod_name in get_deps_for(ec):
                        dep_variants = all_deps_tc_gen.setdefault(dep_name, {})
                        # a variant is defined by version + versionsuffix
                        variant = "version: %s; versionsuffix: %s" % (dep_ver, dep_versuff)
                        # keep track of which easyconfig this is a dependency
                        dep_variants.setdefault(variant, set()).add(ec_file)

            # check which dependencies have more than 1 variant
            for tc_gen, deps in sorted(all_deps.items()):
                for dep, dep_vars in sorted(deps.items()):
                    if not self.check_dep_vars(tc_gen, dep, dep_vars):
                        multi_dep_vars_msg += "Found %s variants of '%s' dependency " % (len(dep_vars), dep)
                        multi_dep_vars_msg += "in easyconfigs using '%s' toolchain generation\n* " % tc_gen
                        multi_dep_vars_msg += '\n  * '.join("%s as dep for %s" % v for v in sorted(dep_vars.items()))
                        multi_dep_vars_msg += '\n'

        if multi_dep_vars_msg:
            self.fail("Should not have multi-variant dependencies in easyconfigs:\n%s" % multi_dep_vars_msg)

    def test_dep_versions_per_toolchain_generation(self):
        """
        Check whether there's only one dependency version per toolchain generation actively used.
        This is enforced to try and limit the chance of running into conflicts when multiple modules built with
        the same toolchain generation are loaded together.
        Active for 2023b generation and newer (GCC 13.2 and newer)
        """
        ecs_by_full_mod_name = {ec['full_mod_name']: ec for ec in self.parsed_easyconfigs}
        if len(ecs_by_full_mod_name) != len(self.parsed_easyconfigs):
            self.fail('Easyconfigs with duplicate full_mod_name found')

        # Cache already determined dependencies
        ec_to_deps = {}

        def get_deps_for(ec):
            """Get list of (direct) dependencies for specified easyconfig."""
            ec_mod_name = ec['full_mod_name']
            deps = ec_to_deps.get(ec_mod_name)
            if deps is None:
                deps = []
                for dep in ec['ec']['dependencies']:
                    dep_mod_name = dep['full_mod_name']
                    deps.append((dep['name'], dep['version'], dep['versionsuffix'], dep_mod_name))
                    # Note: Raises KeyError if dep not found
                    res = ecs_by_full_mod_name[dep_mod_name]
                    deps.extend(get_deps_for(res))
                ec_to_deps[ec_mod_name] = deps
            return deps

        # map GCC(core) version to toolchain generations;
        # only for recent generations, where we want to limit dependency variants as much as possible
        # across all easyconfigs of that generation (regardless of whether a full toolchain or subtoolchain is used);
        # see https://docs.easybuild.io/common-toolchains/#common_toolchains_overview
        gcc_tc_gen_map = {
            '10.2': '2020b',
            '10.3': '2021a',
            '11.1': None,
            '11.2': '2021b',
            '11.3': '2022a',
            '11.4': None,
            '12.1': None,
            '12.2': '2022b',
            '12.3': '2023a',
            '13.1': None,
            '13.1': None,
            '13.2': '2023b',
            '13.3': '2024a',
            '14.1': None,
            '14.2': '2025a',
            '14.3': '2025b',
            '15.1': None,
            '15.2': None,  # maybe 2026a?
        }

        # map intel-compilers to toolchain generations
        # only for recent generations, where we want to limit dependency variants as much as possible
        # across all easyconfigs of that generation (regardless of whether a full toolchain or subtoolchain is used);
        # see https://docs.easybuild.io/common-toolchains/#common_toolchains_overview
        ic_tc_gen_map = {
            '2021.2.0': '2021a',
            '2021.3.0': None,
            '2021.4.0': '2021b',
            '2022.0.1': None,
            '2022.0.2': None,
            '2022.1.0': '2022a',
            '2022.2.0': None,
            '2022.2.1': '2022b',
            '2023.0.0': None,
            '2023.1.0': '2023a',
            '2023.2.1': '2023b',
            '2024.0.0': None,
            '2024.2.0': '2024a',
            '2025.0.0': None,
            '2025.1.0': None,
            '2025.1.1': '2025a',
            '2025.2.0': '2025b',
        }

        multi_dep_vars_msg = ''
        # restrict to checking dependencies of easyconfigs using common toolchains,
        # and GCCcore subtoolchain for common toolchains;
        # for now, we only enforce this for recent toolchain versions (2023b + GCCcore 13.x, and newer);
        patterns = [
            # compiler-only subtoolchains GCCcore and GCC
            r'GCC(core)?-1[3-9]\.[0-9]\.',  # GCCcore 13.x & newer
            # intel-compilers
            r'intel-compilers-202(3\.2|[4-9]\.[0-9])\.[0-9]',  # intel-compilers from 2023.2
            # full toolchains, like foss/2022b or intel/2023a
            r'20(23b|(2[4-9]|[3-9][0-9])[ab])',  # 2023b and newer
        ]

        all_deps = {}

        # collect variants for all dependencies of easyconfigs that use a toolchain that matches
        for ec in self.ordered_specs:
            ec_file = os.path.basename(ec['spec'])
            ec_deps = None

            for pattern in patterns:
                regex = re.compile(r'^.*-(?P<tc_gen>%s).*\.eb$' % pattern)

                # take into account software which also follows a <year>{a,b} versioning scheme
                ec_file = self.multideps_false_positives_regex.sub('', ec_file)

                res = regex.match(ec_file)
                if res:
                    tc_gen = res.group('tc_gen')

                    if tc_gen.startswith('GCC'):
                        gcc_ver = tc_gen.split('-', 1)[1].rstrip('.')
                        if gcc_ver in gcc_tc_gen_map and gcc_tc_gen_map[gcc_ver] is not None:
                            tc_gen = gcc_tc_gen_map[gcc_ver]
                        elif gcc_ver not in gcc_tc_gen_map:
                            # for recent GCC versions, we really want to have a mapping in place...
                            self.fail("No mapping for GCC(core) %s to toolchain generation!" % gcc_ver)

                    if tc_gen.startswith('intel-compilers'):
                        ic_ver = tc_gen.split('-')[2]
                        if ic_ver in ic_tc_gen_map and ic_tc_gen_map[ic_ver] is not None:
                            tc_gen = ic_tc_gen_map[ic_ver]
                        elif ic_ver not in ic_tc_gen_map:
                            # for recent intel-compilers versions, we really want to have a mapping in place...
                            self.fail("No mapping for intel-compilers %s to toolchain generation!" % ic_ver)

                    if ec_deps is None:
                        ec_deps = get_deps_for(ec)

                    all_deps_tc_gen = all_deps.setdefault(tc_gen, {})
                    for dep_name, dep_ver, dep_versuff, _ in ec_deps:
                        dep_variants = all_deps_tc_gen.setdefault(dep_name, {})
                        # a variant is defined by version + versionsuffix
                        variant = "version: %s; versionsuffix: %s" % (dep_ver, dep_versuff)
                        # keep track of which easyconfig this is a dependency
                        dep_variants.setdefault(variant, set()).add(ec_file)

        # check which dependencies have more than 1 variant
        multi_dep_vars, multi_dep_vars_msg = [], ''
        for tc_gen in sorted(all_deps.keys()):
            for dep in sorted(all_deps[tc_gen].keys()):
                dep_vars = all_deps[tc_gen][dep]
                if not self.check_dep_vars(tc_gen, dep, dep_vars):
                    multi_dep_vars.append(dep)
                    multi_dep_vars_msg += "\nfound %s variants of '%s' dependency " % (len(dep_vars), dep)
                    multi_dep_vars_msg += "in easyconfigs using '%s' toolchain generation\n* " % tc_gen
                    multi_dep_vars_msg += '\n* '.join("%s as dep for %s" % v for v in sorted(dep_vars.items()))
                    multi_dep_vars_msg += '\n'

        if multi_dep_vars_msg:
            self.fail("Should not have multi-variant dependencies in easyconfigs:\n%s" % multi_dep_vars_msg)

    def test_downloadable_or_instructions(self):
        """
        Make sure the sources are downloadable or there are instructions for how to download them
        using the download_instructions parameter, including a link if one exists.
        """
        problem_ecs = []
        for easyconfig in self.parsed_easyconfigs:
            ec = easyconfig['ec']
            # easyblocks where there'll be no sources
            if ec['easyblock'] in [
                'BuildEnv',
                'Bundle',
                'CrayToolchain',
                'ModuleRC',
                'SystemCompiler',
                'SystemCompilerGCC',
                'SystemMPI',
                'Toolchain',
            ]:
                continue

            if ec['name'] in [
                # easyconfigs where a dependency provides the source,
                'imkl-FFTW',  # imkl
                'minizip',  # zlib
                # software that have no top-level sources (only components)
                'gnupg-bundle',
            ]:
                continue

            with ec.disable_templating():
                if ec.get('download_instructions') or ec.get('crates') or ec.get('channels') or ec.get('source_urls'):
                    continue

                ok = False
                for source in ec['sources'] + ec['data_sources']:
                    if isinstance(source, dict):
                        if 'git_config' in source or 'source_urls' in source:
                            ok = True
                            break

                for ext in ec['exts_list']:
                    if isinstance(ext, tuple) and len(ext) >= 3:
                        if 'source_urls' in ext[2]:
                            ok = True
                            break

                if 'components' in ec and ec['components']:
                    for component in ec['components']:
                        if len(component) > 2 and not isinstance(component[2], str):
                            if 'source_urls' in component[2]:
                                ok = True
                                break

                if not ok:
                    problem_ecs.append(easyconfig['spec'])

        error_msg = "%d easyconfigs found without defined sources or download_instructions: %s"
        if problem_ecs:
            self.fail(error_msg % (len(problem_ecs), ', '.join(problem_ecs)))

    def test_sanity_check_paths(self):
        """Make sure specified sanity check paths adher to the requirements."""

        for ec in self.parsed_easyconfigs:
            ec_scp = ec['ec'].get('sanity_check_paths', resolve=False)
            if ec_scp != {}:
                # if sanity_check_paths is specified (i.e., non-default), it must adher to the requirements
                # both 'files' and 'dirs' keys, both with list values and with at least one a non-empty list
                error_msg = "sanity_check_paths for %s does not meet requirements: %s" % (ec['spec'], ec_scp)
                self.assertEqual(sorted(ec_scp.keys()), ['dirs', 'files'], error_msg)
                self.assertTrue(isinstance(ec_scp['dirs'], list), error_msg)
                self.assertTrue(isinstance(ec_scp['files'], list), error_msg)
                self.assertTrue(ec_scp['dirs'] or ec_scp['files'], error_msg)

    def test_r_libs_site_env_var(self):
        """Make sure $R_LIBS_SITE is being updated, rather than $R_LIBS."""
        # cfr. https://github.com/easybuilders/easybuild-easyblocks/pull/2326

        r_libs_ecs = []
        for ec in self.parsed_easyconfigs:
            if any('R_LIBS' in ec['ec'].get(key, resolve=False) for key in ('modextrapaths', 'modextravars')):
                r_libs_ecs.append(ec['spec'])

        error_msg = "%d easyconfigs found which set $R_LIBS, should be $R_LIBS_SITE: %s"
        self.assertEqual(r_libs_ecs, [], error_msg % (len(r_libs_ecs), ', '.join(r_libs_ecs)))

    def test_easyconfig_locations(self):
        """Make sure all easyconfigs files are in the right location."""
        easyconfig_dirs_regex = re.compile(r'/easybuild/easyconfigs/[0a-z]/[^/]+$')
        topdir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        for (dirpath, _, filenames) in os.walk(topdir):
            # ignore git/svn dirs & archived easyconfigs
            if '/.git/' in dirpath or '/.svn/' in dirpath or '__archive__' in dirpath:
                continue
            # check whether list of .eb files is non-empty
            easyconfig_files = [fn for fn in filenames if fn.endswith('eb')]
            if easyconfig_files:
                # check whether path matches required pattern
                if not easyconfig_dirs_regex.search(dirpath):
                    if not dirpath.endswith('/easybuild/easyconfigs'):
                        self.fail("There should be no easyconfig files in %s, found %s" % (dirpath, easyconfig_files))

    def test_easybuild_easyconfigs_latest_release(self):
        """
        Check which easyconfig file would be picked up by 'eb --install-latest-eb-release'
        """
        # this mimics the logic used in the find_easybuild_easyconfig used by EasyBuild framework
        # to obtain an easyconfig file when --install-latest-eb-release is used
        topdir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        easybuild_dir = os.path.join(topdir, 'easybuild', 'easyconfigs', 'e', 'EasyBuild')
        ecs = os.listdir(easybuild_dir)

        file_versions = []
        for ec in ecs:
            txt = read_file(os.path.join(easybuild_dir, ec))
            for line in txt.split('\n'):
                if re.search(r'^version\s*=', line):
                    scope = {}
                    exec(line, scope)
                    version = scope['version']
                    file_versions.append((LooseVersion(version), ec))

        most_recent = sorted(file_versions)[-1]
        self.assertEqual(most_recent[0], LooseVersion('5.2.0'))
        self.assertEqual(most_recent[1], 'EasyBuild-5.2.0.eb')

    def test_easyconfig_name_clashes(self):
        """Make sure there is not a name clash when all names are lowercase"""
        topdir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        names = defaultdict(list)
        # ignore git/svn dirs & archived easyconfigs
        ignore_dirs = ['.git', '.svn', '__archive__']
        for (dirpath, _, _) in os.walk(topdir):
            if not any('/%s' % d in dirpath for d in ignore_dirs):
                dirpath_split = dirpath.replace(topdir, '').split(os.sep)
                if len(dirpath_split) == 5:
                    name = dirpath_split[4]
                    names[name.lower()].append(name)

        duplicates = {}
        for name in names:
            if len(names[name]) > 1:
                duplicates[name] = names[name]

        if duplicates:
            self.fail("EasyConfigs with case-insensitive name clash: %s" % duplicates)

    @skip_if_not_pr_to_non_main_branch()
    def test_pr_deprecated_ec_params(self):
        """Check that no deprecated EasyConfig parameters are used."""
        deprecated_params = {old_param: new_param
                             for old_param, (new_param, _) in DEPRECATED_EASYCONFIG_PARAMETERS.items()}
        deprecated_params['parallel'] = 'maxparallel'
        failing_checks = []
        for ec in self.changed_ecs:
            pure_ec = ec.parser.get_config_dict()
            # Special handling:
            for param in pure_ec:
                new_param = deprecated_params.get(param)
                if new_param:
                    ec_fn = os.path.basename(ec.path)
                    failing_checks.append(f"Deprecated parameter '{param}' used in {ec_fn}. "
                                          f"Use '{new_param}' instead.")
        if failing_checks:
            self.fail("\n".join(failing_checks))

    @skip_if_not_pr_to_non_main_branch()
    def test_pr_sha256_checksums(self):
        """Make sure changed easyconfigs have SHA256 checksums in place."""

        # list of software for which checksums can not be required,
        # e.g. because 'source' files need to be constructed manually
        whitelist = [
            'OCaml-*',
        ]

        # filter out deprecated easyconfigs
        retained_changed_ecs = [ec for ec in self.changed_ecs if not ec['deprecated']]

        # The check_sha256_checksums function creates an EasyBlock instance.
        # For easyconfigs using the Bundle easyblock, this is a problem because the 'sources' easyconfig parameter
        # is updated in place (sources for components are added to the 'parent' sources) in Bundle's __init__.
        # Therefore, we need to a operate on a copy of those easyconfigs.
        bundle_easyblocks = {'Bundle', 'CargoPythonBundle', 'PythonBundle', 'EB_OpenSSL_wrapper'}

        def is_bundle(ec):
            return ec['easyblock'] in bundle_easyblocks or ec['name'] == 'Clang-AOMP'
        ecs = [ec.copy() if is_bundle(ec) else ec for ec in retained_changed_ecs]

        # remove checksum for patch_ctypes_ld_library_path for Python easyconfigs, if present;
        # this patch gets added automatically to list of patches by Python easyblock constructor,
        # and causes check_sha256_checksums to fail because an extra checksum is found
        for ec in ecs:
            ec_fn = os.path.basename(ec.path)
            if ec['name'] == 'Python':
                patch_ctypes_ld_library_path = ec.get('patch_ctypes_ld_library_path')
                if patch_ctypes_ld_library_path:
                    checksums = ec.get_ref('checksums')
                    if not isinstance(checksums, list):
                        self.fail(f"Don't know how to handle non-list value type for checksums in {ec_fn}")
                    idx_match = None
                    for idx, entry in enumerate(checksums):
                        if patch_ctypes_ld_library_path in entry:
                            idx_match = idx
                            break
                    if idx_match:
                        del checksums[idx]
                    else:
                        self.fail(f"No checksum found for {patch_ctypes_ld_library_path} in {ec_fn}")

        checksum_issues = check_sha256_checksums(ecs, whitelist=whitelist)
        self.assertTrue(len(checksum_issues) == 0, "No checksum issues:\n%s" % '\n'.join(checksum_issues))

    @skip_if_not_pr_to_non_main_branch()
    def test_pr_python_packages(self):
        """Several checks for easyconfigs that install (bundles of) Python packages."""

        # These packages do not support installation with 'pip'
        whitelist_pip = [
            r'ESMPy-.*',
            r'MATLAB-Engine-.*',
            r'Meld-.*',
            r'PyTorch-.*',
        ]

        whitelist_pip_check = [
            # mympirun is installed with system Python, pip may not be installed for system Python
            r'vsc-mympirun.*',
            # ReFrame intentionally installs its deps in a %(installdir)s/external subdir, which is added
            # to sys.path by the ReFrame command, and is intentionally NOT on the PYTHONPATH.
            # Thus, a pip check fails, but this is expected and ok, it is still a working ReFrame installation
            # See https://github.com/easybuilders/easybuild-easyconfigs/pull/21269 for more info
            r'ReFrame.*',
        ]

        failing_checks = []

        python_default_urls = PythonPackage.extra_options()['source_urls'][0]

        for ec in self.changed_ecs:

            with ec.disable_templating():
                ec_fn = os.path.basename(ec.path)
                easyblock = ec.get('easyblock')
                exts_defaultclass = ec.get('exts_defaultclass')
                exts_default_options = ec.get('exts_default_options', {})

                download_dep_fail = ec.get('download_dep_fail')
                use_pip = ec.get('use_pip')
                if use_pip is None:
                    use_pip = exts_default_options.get('use_pip')

            # only easyconfig parameters as they are defined in the easyconfig file,
            # does *not* include other easyconfig parameters with their default value!
            pure_ec = ec.parser.get_config_dict()

            # download_dep_fail should be set when using PythonPackage
            if easyblock == 'PythonPackage':
                if download_dep_fail is None:
                    failing_checks.append("'download_dep_fail' should be set in %s" % ec_fn)

                if pure_ec.get('source_urls') == python_default_urls:
                    failing_checks.append("'source_urls' should not be defined when using the default value "
                                          "in %s" % ec_fn)

            # --no-build-isolation option for 'pip install' should be enabled
            pip_no_build_isolation = ec.get('pip_no_build_isolation', True)
            for ext in ec.get_ref('exts_list'):
                if isinstance(ext, (tuple, list)) and len(ext) >= 3:
                    ext_opts = ext[2]
                    pip_no_build_isolation &= ext_opts.get('pip_no_build_isolation', True)
            if not pip_no_build_isolation:
                failing_checks.append(f"pip_no_build_isolation should not be disabled in {ec_fn}")

            # use_pip should be set when using PythonPackage or PythonBundle,
            # or an easyblock that derives from it (except for whitelisted easyconfigs)
            if easyblock in ['CargoPythonBundle', 'CargoPythonPackage', 'PythonBundle', 'PythonPackage']:
                if use_pip is None and not any(re.match(regex, ec_fn) for regex in whitelist_pip):
                    failing_checks.append("'use_pip' should be set in %s" % ec_fn)

            if exts_defaultclass == 'PythonPackage':
                # bundle of Python packages should use PythonBundle
                if easyblock == 'Bundle':
                    fail = "'PythonBundle' easyblock should be used for bundle of Python packages in %s" % ec_fn
                    failing_checks.append(fail)

            # if Python is a dependency, that should be reflected in the versionsuffix since v3.8.6
            has_recent_python3_dep = any(LooseVersion(dep['version']) >= LooseVersion('3.8.6')
                                         for dep in ec['dependencies'] if dep['name'] == 'Python')
            has_old_python_dep = any(LooseVersion(dep['version']) < LooseVersion('3.8.6')
                                     for dep in ec['dependencies'] if dep['name'] == 'Python')
            # Tkinter is an exception, since its version always matches the Python version anyway
            # Z3 is an exception, since it has easyconfigs with and without Python bindings
            exception_python_suffix = ['Tkinter', 'Z3']

            if ec.name not in exception_python_suffix:
                if has_old_python_dep and not re.search(r'-Python-[23]\.[0-9]+\.[0-9]+', ec['versionsuffix']):
                    msg = "'-Python-%%(pyver)s' should be included in versionsuffix in %s" % ec_fn
                    # This is only a failure for newly added ECs, not for existing ECS
                    # As that would probably break many ECs
                    if ec_fn in self.added_ecs_filenames:
                        failing_checks.append(msg)
                    else:
                        print('\nNote: Failed non-critical check: ' + msg)
                elif has_recent_python3_dep and re.search(r'-Python-3\.[0-9]+\.[0-9]+', ec['versionsuffix']):
                    msg = "'-Python-%%(pyver)s' should no longer be included in versionsuffix in %s" % ec_fn
                    failing_checks.append(msg)

            # require that running of "pip check" during sanity check is enabled via sanity_pip_check
            if easyblock in ['CargoPythonBundle', 'CargoPythonPackage', 'PythonBundle', 'PythonPackage']:
                sanity_pip_check = ec.get('sanity_pip_check') or exts_default_options.get('sanity_pip_check')
                if not sanity_pip_check and not any(re.match(regex, ec_fn) for regex in whitelist_pip_check):
                    failing_checks.append("sanity_pip_check should be enabled in %s" % ec_fn)
            else:
                # Make sure the user packages in $HOME/.local/lib/python*/ are ignored when running python commands
                # For the EasyBlocks above this is handled automatically by setting $PYTHONNOUSERSITE
                # Detect any code or module invocation (-m or -c), `python cc` and `python <filepath>`
                python_re = re.compile(r'\bpython (-c|-m|cc|[^ ]*\w+.py) ')
                # Detect if `-s` is present, potentially after other switches
                ignore_user_switch_re = re.compile(r'\bpython (-\w+ )*-s ')
                comment_re = re.compile(r'# .*$')
                # Check the raw lines as the issue could be anywhere, not only in `sanity_check_commands`,
                # e.g. `runtest`, `installopts`, `configopts`, ...
                for line_nr, line in enumerate(read_file(ec.path).splitlines()):
                    # Strip comment if present to avoid flagging e.g. "sed '/.../' # Fix 'python -c foo' failure"
                    line = comment_re.sub('', line)
                    if python_re.search(line) and not ignore_user_switch_re.search(line):
                        failing_checks.append("Python invocation in '%s' (line #%s) should use the '-s' parameter in %s"
                                              % (line, line_nr + 1, ec_fn))

            # When using Rust it should use CargoPython*
            if easyblock in ('PythonBundle', 'PythonPackage'):
                if any(dep['name'] == 'Rust' or '-Rust-' in dep['versionsuffix'] for dep in ec.dependencies()):
                    failing_checks.append('Use Cargo%s instead of %s when Rust is used in %s'
                                          % (easyblock, easyblock, ec_fn))

        if failing_checks:
            self.fail('\n'.join(failing_checks))

    @skip_if_not_pr_to_non_main_branch()
    def test_pr_sanity_check_paths(self):
        """Make sure a custom sanity_check_paths value is specified for easyconfigs that use a generic easyblock."""

        # some generic easyblocks already have a decent customised sanity_check_paths,
        # including CargoPythonPackage, CMakePythonPackage, GoPackage, JuliaBundle & JuliaPackage, PerlBundle,
        #           PythonBundle & PythonPackage;
        # BuildEnv, ModuleRC SystemCompiler and Toolchain easyblocks do not install anything so there is nothing
        # to check.
        whitelist = ['BuildEnv', 'CargoPythonBundle', 'CargoPythonPackage', 'CMakePythonPackage',
                     'ConfigureMakePythonPackage', 'CrayToolchain', 'GoPackage', 'JuliaBundle', 'JuliaPackage',
                     'ModuleRC', 'PerlBundle', 'PythonBundle', 'PythonPackage', 'SystemCompiler', 'SystemCompilerGCC',
                     'Toolchain']
        # Bundles of dependencies without files of their own
        # Autotools: Autoconf + Automake + libtool, (recent) GCC: GCCcore + binutils, CUDA: GCC + CUDAcore,
        # CESM-deps: Python + Perl + netCDF + ESMF + git, FEniCS: DOLFIN and co,
        # Jupyter-bundle: JupyterHub + JupyterLab + notebook + nbclassic + jupyter-server-proxy
        # + jupyterlmod + jupyter-resource-usage
        # Python-bundle: Python + SciPy-bundle + matplotlib + JupyterLab
        bundles_whitelist = ['Autotools', 'CESM-deps', 'CUDA', 'ESL-Bundle', 'FEniCS', 'GCC', 'Jupyter-bundle',
                             'Python-bundle', 'ROCm', 'llvm-compilers']

        failing_checks = []

        for ec in self.changed_ecs:
            easyblock = ec.get('easyblock')
            if is_generic_easyblock(easyblock) and not ec.get('sanity_check_paths'):

                sanity_check_ok = False

                if easyblock in whitelist or (easyblock == 'Bundle' and ec['name'] in bundles_whitelist):
                    sanity_check_ok = True

                # also allow bundles that enable per-component sanity checks
                elif easyblock == 'Bundle':
                    if ec['sanity_check_components'] or ec['sanity_check_all_components']:
                        sanity_check_ok = True

                if not sanity_check_ok:
                    ec_fn = os.path.basename(ec.path)
                    failing_checks.append("No custom sanity_check_paths found in %s" % ec_fn)

        self.assertFalse(failing_checks, '\n'.join(failing_checks))

    @skip_if_not_pr_to_non_main_branch()
    def test_pr_https(self):
        """Make sure https:// URL is used (if it exists) for homepage/source_urls (rather than http://)."""

        whitelist = [
            'PycURL',  # bad certificate for https://pycurl.io/
        ]
        url_whitelist = [
        ]
        # Cache: Mapping of already checked HTTP urls to whether the HTTPS variant works
        checked_urls = {}

        def check_https_url(http_url):
            """Check if the https url works"""
            http_url = http_url.rstrip('/')  # Remove trailing slashes
            https_url_works = checked_urls.get(http_url)
            if https_url_works is None:
                https_url = http_url.replace('http://', 'https://')
                try:
                    req = Request(https_url, None, {'User-Agent': 'EasyBuild', 'Accept': '*/*'})
                    https_url_works = bool(urlopen(req, timeout=5))
                except Exception:
                    https_url_works = False
            checked_urls[http_url] = https_url_works

        http_regex = re.compile('http://[^"\'\n]+', re.M)

        failing_checks = []
        for ec in self.changed_ecs:
            ec_fn = os.path.basename(ec.path)

            # skip whitelisted easyconfigs
            if any(ec_fn.startswith(x) for x in whitelist):
                continue

            # ignore commented out lines in easyconfig files when checking for http:// URLs
            ec_txt = '\n'.join(line for line in ec.rawtxt.split('\n') if not line.startswith('#'))

            for http_url in http_regex.findall(ec_txt):

                # skip whitelisted http:// URLs
                if any(http_url.startswith(x) for x in url_whitelist):
                    continue

                if check_https_url(http_url):
                    failing_checks.append("Found http:// URL in %s, should be https:// : %s" % (ec_fn, http_url))
        if failing_checks:
            self.fail('\n'.join(failing_checks))

    @skip_if_not_pr_to_non_main_branch()
    def test_ec_file_permissions(self):
        """Make sure correct access rights are set for easyconfigs."""

        failing_checks = []
        for ec in self.changed_ecs:
            ec_fn = os.path.basename(ec.path)
            st = os.stat(ec.path)
            read_perms = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
            exec_perms = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            wrong_perms = []
            if (st.st_mode & read_perms) != read_perms:
                wrong_perms.append("readable (owner, group, other)")
            if st.st_mode & exec_perms:
                wrong_perms.append("not executable")
            if not (st.st_mode & stat.S_IWUSR):
                wrong_perms.append("at least owner writable")
            if wrong_perms:
                failing_checks.append("%s must be %s, is: %s" % (ec_fn, ", ".join(wrong_perms), oct(st.st_mode)))

        if failing_checks:
            self.fail('\n'.join(failing_checks))

    @skip_if_not_pr_to_non_main_branch()
    def test_pr_CMAKE_BUILD_TYPE(self):
        """Make sure -DCMAKE_BUILD_TYPE is no longer used (replaced by build_type)"""
        failing_checks = []
        for ec in self.changed_ecs:
            ec_fn = os.path.basename(ec.path)
            build_type = ec.get_ref('build_type') if 'build_type' in ec else ''
            configopts = ec.get_ref('configopts')
            if isinstance(configopts, list):
                configopts = ' '.join(configopts)

            if configopts and '-DCMAKE_BUILD_TYPE' in configopts:
                failing_checks.append("Found -DCMAKE_BUILD_TYPE in configopts. Use build_type instead: %s" % ec_fn)
            if build_type == 'Release':
                failing_checks.append("build_type was set to the default of 'Release'. "
                                      "Omit this to base it on toolchain_opts.debug: %s" % ec_fn)
        if failing_checks:
            self.fail('\n'.join(failing_checks))

    @skip_if_not_pr_to_non_main_branch()
    def test_pr_CMAKE_INSTALL_LIBDIR(self):
        """Make sure -DCMAKE_INSTALL_LIBDIR is no longer used (replaced by install_libdir)"""
        failing_checks = []
        for ec in self.changed_ecs:
            ec_fn = os.path.basename(ec.path)
            configopts = ec.get_ref('configopts')
            if isinstance(configopts, list):
                configopts = ' '.join(configopts)

            cmake_install_opt_pattern = re.compile(r"-DCMAKE_INSTALL_LIBDIR(:PATH)?=[^\s]")
            if cmake_install_opt_pattern.search(configopts):
                failing_checks.append(
                    "Found -DCMAKE_INSTALL_LIBDIR in configopts. Use install_libdir instead: %s" % ec_fn
                )

        if failing_checks:
            self.fail('\n'.join(failing_checks))

    @skip_if_not_pr_to_non_main_branch()
    def test_pr_patch_descr(self):
        """
        Check whether all patch files touched in PR have a description on top.
        """
        no_descr_patches = []
        for patch in self.changed_patches:
            patch_txt = read_file(patch)
            if patch_txt.startswith('--- '):
                no_descr_patches.append(patch)

        self.assertFalse(no_descr_patches, "No description found in patches: %s" % ', '.join(no_descr_patches))


def verify_patch(specdir, patch_spec, checksum_idx, patch_checksums, extension_name=None):
    """Verify existance and checksum of the given patch.

    specdir         - Directory of the easyconfig
    patch_spec      - Patch entry
    checksum_idx    - Expected index in the checksum list
    patch_checksums - List of checksums for patches
    extension_name  - Name of the extensions this patch is for if any

    Return a (possibly empty) list of failure messages
    """
    patch_dir = specdir
    if isinstance(patch_spec, str):
        patch_name = patch_spec
    elif isinstance(patch_spec, (tuple, list)):
        patch_name = patch_spec[0]
    elif isinstance(patch_spec, dict):
        patch_name = patch_spec['name']
        alt_location = patch_spec.get('alt_location')
        if alt_location:
            basedir = os.path.dirname(os.path.dirname(specdir))
            patch_dir = os.path.join(basedir, letter_dir_for(alt_location), alt_location)
    else:
        # Should have already been verified
        raise RuntimeError('Patch spec is not a string, tuple, list or dict: %s\nType: %s' % (patch_spec,
                                                                                              type(patch_spec)))

    patch_path = os.path.join(patch_dir, patch_name)
    # only check actual patch files, not other files being copied via the patch functionality
    if patch_path.endswith('.patch'):
        patch_descr = f"patch file {patch_name}"
        if extension_name:
            patch_descr += f" of extension {extension_name}"

        if not os.path.isfile(patch_path):
            return [f"{patch_descr} is missing"]

        if checksum_idx < len(patch_checksums):
            checksum = patch_checksums[checksum_idx]
            if not verify_checksum(patch_path, checksum):
                return [f"Invalid checksum for {patch_descr}: {checksum}"]

    return []  # No error


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

        # cache the parsed easyconfig, to avoid that it is parsed again
        EasyConfigTest._parsed_easyconfigs.append(ecs[0])
    else:
        self.fail("easyconfig %s does not contain blocks, yields only one parsed easyconfig" % spec)

    # check easyconfig file name
    expected_fn = '%s-%s.eb' % (ec['name'], det_full_ec_version(ec))
    msg = "Filename '%s' of parsed easyconfig matches expected filename '%s'" % (spec, expected_fn)
    self.assertEqual(os.path.basename(spec), expected_fn, msg)

    name, easyblock = fetch_parameters_from_easyconfig(ec.rawtxt, ['name', 'easyblock'])

    # make sure easyconfig file is in expected location
    expected_subdir = os.path.join('easybuild', 'easyconfigs', letter_dir_for(name), name)
    subdir = os.path.join(*spec.split(os.path.sep)[-5:-1])
    fail_msg = "Easyconfig file %s not in expected subdirectory %s" % (spec, expected_subdir)
    self.assertEqual(expected_subdir, subdir, fail_msg)

    # sanity check for software name, moduleclass
    self.assertEqual(ec['name'], name)
    self.assertTrue(ec['moduleclass'] in build_option('valid_module_classes'))
    # base is the default value for moduleclass, which should never be used,
    # and moduleclass should always be set in the easyconfig file
    self.assertNotEqual(ec['moduleclass'], 'base',
                        "moduleclass should be set, and not be set to 'base', for %s" % spec)

    # instantiate easyblock with easyconfig file
    app_class = get_easyblock_class(easyblock, name=name)

    # check that automagic fallback to ConfigureMake isn't done (deprecated behaviour)
    fn = os.path.basename(spec)
    error_msg = "%s relies on automagic fallback to ConfigureMake, should use easyblock = 'ConfigureMake' instead" % fn
    self.assertTrue(easyblock or app_class is not ConfigureMake, error_msg)

    # dump the easyconfig file;
    # this should be done before creating the easyblock instance (done below via app_class),
    # because some easyblocks (like PythonBundle) modify easyconfig parameters at initialisation
    handle, test_ecfile = tempfile.mkstemp()
    os.close(handle)

    ec.dump(test_ecfile)
    dumped_ec = EasyConfigParser(test_ecfile).get_config_dict()
    os.remove(test_ecfile)

    app = app_class(ec)

    # more sanity checks
    self.assertEqual(name, app.name)
    self.assertEqual(ec['version'], app.version)

    failing_checks = []

    # make sure that deprecated 'dummy' toolchain is no longer used, should use 'system' toolchain instead
    if ec['toolchain']['name'] == 'dummy':
        failing_checks.append("%s should use 'system' toolchain rather than deprecated 'dummy' toolchain")

    # make sure that $root is not used, since it is not compatible with module files in Lua syntax
    res = re.findall(r'.*\$root.*', ec.rawtxt, re.M)
    if res:
        failing_checks.append("Found use of '$root', not compatible with modules in Lua syntax, "
                              "use '%%(installdir)s' instead: %s" % res)

    # check for redefined easyconfig parameters, there should be none...
    param_def_regex = re.compile(r'^(?P<key>\w+)\s*=', re.M)
    keys = param_def_regex.findall(ec.rawtxt)
    redefined_keys = []
    for key in sorted(nub(keys)):
        cnt = keys.count(key)
        if cnt > 1:
            redefined_keys.append((key, cnt))

    if redefined_keys:
        failing_checks.append("There should be no redefined easyconfig parameters, found %d: " % len(redefined_keys) +
                              ', '.join('%s (%d)' % x for x in redefined_keys))

    # make sure that download_dep_fail, use_pip, sanity_pip_check are not explicitly enabled,
    # since they are enabled by default now in PythonPackage easyblock
    patterns = [
        # top-level easyconfig parameters
        """^download_dep_fail = True""",
        """^sanity_pip_check = True""",
        """^use_pip = True""",
        # for specific extensions, or in exts_default_options
        """["']download_dep_fail["']: True""",
        """["']sanity_pip_check["']: True""",
        """["']use_pip["']: True""",
    ]
    hits = []
    for pattern in patterns:
        regex = re.compile(pattern, re.M)
        hits += regex.findall(ec.rawtxt)

    error_msg = "download_dep_fail, sanity_pip_check, use_pip should not be set to True "
    error_msg += "(already enabled by default in PythonPackage easyblock)"
    self.assertFalse(hits, error_msg)

    # make sure old GitHub urls for EasyBuild that include 'hpcugent' are no longer used
    old_urls = [
        'github.com/hpcugent/easybuild',
        'hpcugent.github.com/easybuild',
        'hpcugent.github.io/easybuild',
    ]
    failing_checks.extend("Old URL '%s' found" % old_url for old_url in old_urls if old_url in ec.rawtxt)

    # Note the use of app.cfg which might contain sources populated by e.g. the Cargo easyblock
    sources, patches, checksums = app.cfg.get_ref('sources'), app.cfg['patches'], app.cfg['checksums']
    post_install_patches = app.cfg['postinstallpatches']

    # make sure binutils is included as a (build) dep if toolchain is GCCcore
    if ec['toolchain']['name'] == 'GCCcore':
        # easyblocks without a build step
        non_build_blocks = ['Binary', 'JAR', 'PackedBinary', 'Tarball', 'EB_VSCode']
        # some software packages do not have a build step
        non_build_soft = ['ANIcalculator', 'Eigen']

        requires_binutils = ec['easyblock'] not in non_build_blocks and ec['name'] not in non_build_soft

        # let's also exclude the very special case where the system GCC is used as GCCcore, and only apply this
        # exception to the dependencies of binutils (since we should eventually build a new binutils with GCCcore)
        if ec['toolchain']['version'] == 'system':
            binutils_complete_dependencies = ['M4', 'Bison', 'flex', 'help2man', 'zlib', 'binutils']
            requires_binutils &= bool(ec['name'] not in binutils_complete_dependencies)

        # if no sources/extensions/components are specified, it's just a bundle (nothing is being compiled)
        requires_binutils &= bool(sources or ec.get_ref('exts_list') or ec.get_ref('components'))

        if requires_binutils:
            # dependencies() returns both build and runtime dependencies
            # in some cases, binutils can also be a runtime dep (e.g. for Clang)
            # Also using GCC directly as a build dep is also allowed (it includes the correct binutils)
            dep_names = [d['name'] for d in ec.dependencies()]
            if 'binutils' not in dep_names and 'GCC' not in dep_names:
                failing_checks.append("binutils or GCC is a build dep: " + str(dep_names))

    # make sure that OpenSSL wrapper is used rather than OS dependency,
    # for easyconfigs using a 2021a (sub)toolchain or more recent common toolchain version
    osdeps = ec['osdependencies']
    if osdeps:
        # check whether any entry in osdependencies related to OpenSSL
        openssl_osdep = False
        for osdep in osdeps:
            if isinstance(osdep, str):
                osdep = [osdep]
            if any('libssl' in x for x in osdep) or any('openssl' in x for x in osdep):
                openssl_osdep = True

        if openssl_osdep:
            tcname = ec['toolchain']['name']
            tcver = LooseVersion(ec['toolchain']['version'])

            gcc_subtc_2021a = tcname in ('GCCcore', 'GCC') and tcver > LooseVersion('10.3')
            if gcc_subtc_2021a or (tcname in ('foss', 'gompi', 'iimpi', 'intel') and tcver >= LooseVersion('2021')):
                if openssl_osdep:
                    failing_checks.append("OpenSSL should not be listed as OS dependency")

    src_cnt = len(sources)
    patch_checksums = checksums[src_cnt:]

    # make sure all patch files are available
    specdir = os.path.dirname(spec)

    for idx, patch in enumerate(patches + post_install_patches):
        failing_checks.extend(verify_patch(specdir, patch, idx, patch_checksums))

    # make sure 'fetch' step is not being skipped, since that implies not verifying the checksum
    if checksums and ('fetch' in ec['skipsteps']):
        failing_checks.append("'fetch' step should not be skipped, since that implies not verifying checksums")

    extension_names = set()
    for ext in ec.get_ref('exts_list'):
        if isinstance(ext, (tuple, list)):
            ext_name = ext[0]
            if len(ext) == 3 and not isinstance(ext[2], dict):
                failing_checks.append("3rd element of extension spec for %s must be a dictionary" % ext_name)
        else:
            ext_name = ext
        if ext_name in extension_names:
            failing_checks.append(f'{ext_name} was added multiple times to exts_list')
        else:
            extension_names.add(ext_name)

    # Need to check now as collect_exts_file_info relies on correct exts_list
    if failing_checks:
        self.fail('Verification for %s failed:\n' % os.path.basename(spec) + '\n'.join(set(failing_checks)))

    # After the sanity check above, use collect_exts_file_info to resolve templates etc. correctly
    for ext in app.collect_exts_file_info(fetch_files=False, verify_checksums=False):
        try:
            ext_options = ext['options']
        except KeyError:
            # No options --> Only have a name which is valid, so nothing to check
            continue

        checksums = ext_options.get('checksums', [])
        src_cnt = len(ext_options.get('sources', [])) or 1
        patch_checksums = checksums[src_cnt:]

        for idx, ext_patch in enumerate(ext.get('patches', [])):
            failing_checks.extend(verify_patch(specdir, ext_patch, idx, patch_checksums, extension_name=ext_name))

    # check whether all extra_options defined for used easyblock are defined
    extra_opts = app.extra_options()
    for key in extra_opts:
        if key not in app.cfg:
            failing_checks.append("Missing extra_option '%s'" % key)

    app.close_log()
    os.remove(app.logfile)

    # inject dummy values for templates that are only known at a later stage
    dummy_template_values = {
        'builddir': '/dummy/builddir',
        'installdir': '/dummy/installdir',
        'startdir': '/dummy/startdir',
        'parallel': '2',
    }
    ec.template_values.update(dummy_template_values)

    ec_dict = ec.parser.get_config_dict()
    orig_toolchain = ec_dict['toolchain']
    for key in ec_dict:
        # skip parameters for which value is equal to default value
        orig_val = ec_dict[key]
        if key in DEFAULT_CONFIG and orig_val == DEFAULT_CONFIG[key][0]:
            continue
        if key in extra_opts and orig_val == extra_opts[key][0]:
            continue
        if key not in DEFAULT_CONFIG and key not in extra_opts:
            continue

        orig_val = resolve_template(ec_dict[key], ec.template_values, expect_resolved=False)
        dumped_val = resolve_template(dumped_ec[key], ec.template_values, expect_resolved=False)

        # take into account that dumped value for *dependencies may include hard-coded subtoolchains
        # if no easyconfig was found for the dependency with the 'parent' toolchain,
        # if may get resolved using a subtoolchain, which is then hardcoded in the dumped easyconfig
        if key in DEPENDENCY_PARAMETERS:
            # number of dependencies should remain the same
            if len(orig_val) != len(dumped_val):
                failing_checks.append("Length difference for %s: %s vs %s" % (key, orig_val, dumped_val))
                continue
            for orig_dep, dumped_dep in zip(orig_val, dumped_val):
                # name should always match
                if orig_dep[0] != dumped_dep[0]:
                    failing_checks.append("Different name in %s: %s vs %s" % (key, orig_dep[0], dumped_dep[0]))

                desc = '%s of %s' % (orig_dep[0], key)
                # version should always match, or be a possibility from the version dict
                if isinstance(orig_dep[1], dict):
                    if dumped_dep[1] not in orig_dep[1].values():
                        failing_checks.append("Wrong version in %s: %s vs %s"
                                              % (desc, dumped_dep[1], orig_dep[1].values()))
                elif orig_dep[1] != dumped_dep[1]:
                    failing_checks.append("Different version in %s: %s vs %s" % (desc, orig_dep[1], dumped_dep[1]))

                # 3rd value is versionsuffix;
                if len(dumped_dep) >= 3:
                    # if no versionsuffix was specified in original dep spec, then dumped value should be empty string
                    if len(orig_dep) >= 3:
                        if orig_dep[2] != dumped_dep[2]:
                            failing_checks.append("Different versionsuffix in %s: %s vs %s"
                                                  % (desc, orig_dep[2], dumped_dep[2]))
                    elif dumped_dep[2] != '':
                        failing_checks.append("Unexpected versionsuffix in %s: %s" % (desc, dumped_dep[2]))

                # 4th value is toolchain spec
                if len(dumped_dep) >= 4:
                    if len(orig_dep) >= 4:
                        # use of `True` is deprecated in favour of the more intuitive `SYSTEM` template
                        if orig_dep[3] is True:
                            failing_checks.append(
                                "use of `True` to indicate the system toolchain for "
                                "%s is deprecated, use the `SYSTEM` template constant instead" % desc
                            )
                        elif orig_dep[3] != dumped_dep[3]:
                            failing_checks.append("Different toolchain in %s: %s vs %s"
                                                  % (desc, orig_dep[3], dumped_dep[3]))
                    else:
                        # if a subtoolchain is specifed (only) in the dumped easyconfig,
                        # it should *not* be the same as the parent toolchain
                        parent_tc = (orig_toolchain['name'], orig_toolchain['version'])
                        if dumped_dep[3] == parent_tc:
                            failing_checks.append("Explicit toolchain in %s should not be the parent toolchain (%s)"
                                                  % (desc, parent_tc))

        # take into account that for some string-valued easyconfig parameters (configopts & co),
        # the easyblock may have injected additional values, which affects the dumped easyconfig file
        elif isinstance(orig_val, str):
            if not dumped_val.startswith(orig_val):
                failing_checks.append(f"{key} value '{dumped_val}' should start with '{orig_val}'")
        elif orig_val != dumped_val:
            fail_msg = f"{key} value should be equal in original and dumped easyconfig: "
            fail_msg += f"'{orig_val}' vs '{dumped_val}'"
            failing_checks.append(fail_msg)

    modextrapaths = ec.get('modextrapaths', {}, resolve=True)
    regex = re.compile(r'^lib*/python[0-9]\.[0-9]+/site-packages$')
    for key, value in modextrapaths.items():
        # don't allow updating of $PYTHONPATH with standard lib/python*/site-packages path,
        # since that's already taken care of by EasyBuild framework now
        # (cfr. https://github.com/easybuilders/easybuild-framework/pull/4539)
        if key == 'PYTHONPATH':
            if isinstance(value, str):
                value = [value]
            if any(regex.match(x) for x in value):
                fail_msg = "PYTHONPATH should not be specified in modextrapaths with standard path that matches "
                fail_msg += f"'{regex.pattern}'"
                failing_checks.append(fail_msg)
        # don't allow hardcoding 'CPATH' in modextrapaths, should use MODULE_LOAD_ENV_HEADERS constant instead
        if key == 'CPATH':
            fail_msg = "'CPATH' should not be used in modextrapaths, use MODULE_LOAD_ENV_HEADERS constant instead"
            failing_checks.append(fail_msg)

    # meson buildtype should be specified with easyblock parameter "buildtype" not with custom configopts.
    if ec['easyblock'] == 'MesonNinja':
        configopts = ec.get('configopts', '', resolve=False)
        if '--buildtype ' in configopts or '--buildtype=' in configopts:
            fail_msg = "Build type should be specified via MesonNinja parameter 'buildtype' instead of configopts."
            failing_checks.append(fail_msg)

    if failing_checks:
        self.fail('Verification for %s failed:\n' % os.path.basename(spec) + '\n'.join(failing_checks))

    # test passed, so set back
    single_tests_ok = prev_single_tests_ok


def suite(loader=None):
    """Return all easyblock initialisation tests."""
    def make_inner_test(spec_path):
        def innertest(self):
            template_easyconfig_test(self, spec_path)
        return innertest

    # dynamically generate a separate test for each of the available easyconfigs
    # define new inner functions that can be added as class methods to InitTest
    easyconfigs_path = get_paths_for('easyconfigs')[0]
    cnt = 0
    for (subpath, dirs, specs) in os.walk(easyconfigs_path, topdown=True):

        # ignore archived easyconfigs
        if '__archive__' in dirs:
            dirs.remove('__archive__')

        for spec in specs:
            if spec.endswith('.eb'):
                cnt += 1
                innertest = make_inner_test(os.path.join(subpath, spec))
                innertest.__doc__ = "Test for easyconfig %s" % spec
                # double underscore so parsing tests are run first
                innertest.__name__ = "test__parse_easyconfig_%s" % spec
                setattr(EasyConfigTest, innertest.__name__, innertest)

    print("Found %s easyconfigs..." % cnt)
    if not loader:
        loader = TestLoader()
    return loader.loadTestsFromTestCase(EasyConfigTest)


if __name__ == '__main__':
    main()
