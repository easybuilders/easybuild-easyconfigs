##
# Copyright 2013-2021 Ghent University
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
import sys
import tempfile
from distutils.version import LooseVersion
from unittest import TestCase, TestLoader, main

import easybuild.main as eb_main
import easybuild.tools.options as eboptions
from easybuild.base import fancylogger
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig.default import DEFAULT_CONFIG
from easybuild.framework.easyconfig.format.format import DEPENDENCY_PARAMETERS
from easybuild.framework.easyconfig.easyconfig import get_easyblock_class, letter_dir_for
from easybuild.framework.easyconfig.easyconfig import resolve_template
from easybuild.framework.easyconfig.parser import EasyConfigParser, fetch_parameters_from_easyconfig
from easybuild.framework.easyconfig.tools import check_sha256_checksums, dep_graph, get_paths_for, process_easyconfig
from easybuild.tools import config
from easybuild.tools.config import GENERAL_CLASS, build_option
from easybuild.tools.filetools import change_dir, read_file, remove_file, write_file, is_generic_easyblock
from easybuild.tools.module_naming_scheme.utilities import det_full_ec_version
from easybuild.tools.modules import modules_tool
from easybuild.tools.py2vs3 import string_type, urlopen
from easybuild.tools.robot import check_conflicts, resolve_dependencies
from easybuild.tools.run import run_cmd
from easybuild.tools.options import set_tmpdir
from easybuild.tools.utilities import nub


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
    del eb_go

    # put dummy 'craype-test' module in place, which is required for parsing easyconfigs using Cray* toolchains
    TMPDIR = tempfile.mkdtemp()
    os.environ['MODULEPATH'] = TMPDIR
    write_file(os.path.join(TMPDIR, 'craype-test'), '#%Module\n')

    log = fancylogger.getLogger("EasyConfigTest", fname=False)

    # make sure a logger is present for main
    eb_main._log = log
    ordered_specs = None
    parsed_easyconfigs = []

    def process_all_easyconfigs(self):
        """Process all easyconfigs and resolve inter-easyconfig dependencies."""
        # all available easyconfig files
        easyconfigs_path = get_paths_for("easyconfigs")[0]
        specs = glob.glob('%s/*/*/*.eb' % easyconfigs_path)

        # parse all easyconfigs if they haven't been already
        if not EasyConfigTest.parsed_easyconfigs:
            for spec in specs:
                EasyConfigTest.parsed_easyconfigs.extend(process_easyconfig(spec))

        # filter out external modules
        for ec in EasyConfigTest.parsed_easyconfigs:
            for dep in ec['dependencies'][:]:
                if dep.get('external_module', False):
                    ec['dependencies'].remove(dep)

        EasyConfigTest.ordered_specs = resolve_dependencies(
            EasyConfigTest.parsed_easyconfigs, modules_tool(), retain_all_deps=True)

    def test_dep_graph(self):
        """Unit test that builds a full dependency graph."""
        # pygraph dependencies required for constructing dependency graph are not available prior to Python 2.6
        if LooseVersion(sys.version) >= LooseVersion('2.6') and single_tests_ok:
            # temporary file for dep graph
            (hn, fn) = tempfile.mkstemp(suffix='.dot')
            os.close(hn)

            if EasyConfigTest.ordered_specs is None:
                self.process_all_easyconfigs()

            dep_graph(fn, EasyConfigTest.ordered_specs)

            remove_file(fn)
        else:
            print("(skipped dep graph test)")

    def test_conflicts(self):
        """Check whether any conflicts occur in software dependency graphs."""

        if not single_tests_ok:
            print("(skipped conflicts test)")
            return

        if EasyConfigTest.ordered_specs is None:
            self.process_all_easyconfigs()

        self.assertFalse(check_conflicts(EasyConfigTest.ordered_specs, modules_tool(), check_inter_ec_conflicts=False),
                         "No conflicts detected")

    def check_dep_vars(self, dep, dep_vars):
        """Check whether available variants of a particular dependency are acceptable or not."""

        # 'guilty' until proven 'innocent'
        res = False

        # filter out wrapped Java versions
        # i.e. if the version of one is a prefix of the version of the other one (e.g. 1.8 & 1.8.0_181)
        if dep == 'Java':
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

        # filter out binutils with empty versionsuffix which is used to build toolchain compiler
        if dep == 'binutils' and len(dep_vars) > 1:
            empty_vsuff_vars = [v for v in dep_vars.keys() if v.endswith('versionsuffix: ')]
            if len(empty_vsuff_vars) == 1:
                dep_vars = dict((k, v) for (k, v) in dep_vars.items() if k != empty_vsuff_vars[0])

        # multiple variants of HTSlib is OK as long as they are deps for a matching version of BCFtools;
        # same goes for WRF and WPS
        for dep_name, parent_name in [('HTSlib', 'BCFtools'), ('WRF', 'WPS')]:
            if dep == dep_name and len(dep_vars) > 1:
                for key in list(dep_vars):
                    ecs = dep_vars[key]
                    # filter out dep variants that are only used as dependency for parent with same version
                    dep_ver = re.search('^version: (?P<ver>[^;]+);', key).group('ver')
                    if all(ec.startswith('%s-%s-' % (parent_name, dep_ver)) for ec in ecs) and len(dep_vars) > 1:
                        dep_vars.pop(key)

        # multiple versions of Boost is OK as long as they are deps for a matching Boost.Python
        if dep == 'Boost' and len(dep_vars) > 1:
            for key in list(dep_vars):
                ecs = dep_vars[key]
                # filter out Boost variants that are only used as dependency for Boost.Python with same version
                boost_ver = re.search('^version: (?P<ver>[^;]+);', key).group('ver')
                if all(ec.startswith('Boost.Python-%s-' % boost_ver) for ec in ecs):
                    dep_vars.pop(key)

        # filter out FFTW and imkl with -serial versionsuffix which are used in non-MPI subtoolchains
        if dep in ['FFTW', 'imkl']:
            serial_vsuff_vars = [v for v in dep_vars.keys() if v.endswith('versionsuffix: -serial')]
            if len(serial_vsuff_vars) == 1:
                dep_vars = dict((k, v) for (k, v) in dep_vars.items() if k != serial_vsuff_vars[0])

        # filter out BLIS and libFLAME with -amd versionsuffix
        # (AMD forks, used in gobff/*-amd toolchains)
        if dep in ['BLIS', 'libFLAME']:
            amd_vsuff_vars = [v for v in dep_vars.keys() if v.endswith('versionsuffix: -amd')]
            if len(amd_vsuff_vars) == 1:
                dep_vars = dict((k, v) for (k, v) in dep_vars.items() if k != amd_vsuff_vars[0])

        # filter out ScaLAPACK with -BLIS-* versionsuffix, used in goblf toolchain
        if dep == 'ScaLAPACK':
            blis_vsuff_vars = [v for v in dep_vars.keys() if '; versionsuffix: -BLIS-' in v]
            if len(blis_vsuff_vars) == 1:
                dep_vars = dict((k, v) for (k, v) in dep_vars.items() if k != blis_vsuff_vars[0])

        # for some dependencies, we allow exceptions for software that depends on a particular version,
        # as long as that's indicated by the versionsuffix
        if dep in ['ASE', 'Boost', 'Java', 'Lua', 'PLUMED', 'PyTorch', 'R', 'TensorFlow'] and len(dep_vars) > 1:
            for key in list(dep_vars):
                dep_ver = re.search('^version: (?P<ver>[^;]+);', key).group('ver')
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

        # filter out variants that are specific to a particular version of CUDA
        cuda_dep_vars = [v for v in dep_vars.keys() if '-CUDA' in v]
        if len(dep_vars) > len(cuda_dep_vars):
            for key in list(dep_vars):
                if re.search('; versionsuffix: .*-CUDA-[0-9.]+', key):
                    dep_vars.pop(key)

        # some software packages require a specific (older/newer) version of a particular dependency
        old_dep_versions = {
            # EMAN2 2.3 requires Boost(.Python) 1.64.0
            'Boost': [('1.64.0;', [r'Boost.Python-1\.64\.0-', r'EMAN2-2\.3-'])],
            'Boost.Python': [('1.64.0;', [r'EMAN2-2\.3-'])],
            # Kraken 1.x requires Jellyfish 1.x (Roary & metaWRAP depend on Kraken 1.x)
            'Jellyfish': [(r'1\.', [r'Kraken-1\.', r'Roary-3\.12\.0', r'metaWRAP-1\.2'])],
            # Libint 1.1.6 is required by older CP2K versions
            'Libint': [(r'1\.1\.6', [r'CP2K-[3-6]'])],
            # libxc 2.x or 3.x is required by ABINIT, AtomPAW, CP2K, GPAW, horton, PySCF, WIEN2k
            # (Qiskit depends on PySCF)
            'libxc': [(r'[23]\.', [r'ABINIT-', r'AtomPAW-', r'CP2K-', r'GPAW-', r'horton-',
                                   r'PySCF-', r'Qiskit-', r'WIEN2k-'])],
            # numba 0.47.x requires LLVM 7.x or 8.x (see https://github.com/numba/llvmlite#compatibility)
            # both scVelo and Python-Geometric depend on numba
            'LLVM': [(r'8\.', [r'numba-0\.47\.0-', r'scVelo-0\.1\.24-', r'PyTorch-Geometric-1\.[34]\.2'])],
            # rampart requires nodejs > 10, artic-ncov2019 requires rampart
            'nodejs': [('12.16.1', ['rampart-1.2.0rc3-', 'artic-ncov2019-2020.04.13'])],
            # OPERA requires SAMtools 0.x
            'SAMtools': [(r'0\.', [r'ChimPipe-0\.9\.5', r'Cufflinks-2\.2\.1', r'OPERA-2\.0\.6',
                                   r'CGmapTools-0\.1\.2', r'BatMeth2-2\.1'])],
            'TensorFlow': [
                # medaka 0.11.4/0.12.0 requires recent TensorFlow <= 1.14 (and Python 3.6),
                # artic-ncov2019 requires medaka
                ('1.13.1;', ['medaka-0.11.4-', 'medaka-0.12.0-', 'artic-ncov2019-2020.04.13']),
                # medaka 1.1.* and 1.2.* requires TensorFlow 2.2.0
                # (while other 2019b easyconfigs use TensorFlow 2.1.0 as dep);
                # TensorFlow 2.2.0 is also used as a dep for Horovod 0.19.5;
                # decona 0.1.2 and NGSpeciesID 0.1.1.1 depend on medaka 1.1.3
                ('2.2.0;', ['medaka-1.2.[0]-', 'medaka-1.1.[13]-', 'Horovod-0.19.5-', 'decona-0.1.2-',
                            'NGSpeciesID-0.1.1.1-']),
            ],
            # medaka 1.1.* and 1.2.* requires Pysam 0.16.0.1,
            # which is newer than what others use as dependency w.r.t. Pysam version in 2019b generation;
            # decona 0.1.2 and NGSpeciesID 0.1.1.1 depend on medaka 1.1.3
            'Pysam': [('0.16.0.1;', ['medaka-1.2.[0]-', 'medaka-1.1.[13]-', 'decona-0.1.2-',
                      'NGSpeciesID-0.1.1.1-'])],
        }
        if dep in old_dep_versions and len(dep_vars) > 1:
            for key in list(dep_vars):
                for version_pattern, parents in old_dep_versions[dep]:
                    # filter out known old dependency versions
                    if re.search('^version: %s' % version_pattern, key):
                        # only filter if the easyconfig using this dep variants is known
                        if all(any(re.search(p, x) for p in parents) for x in dep_vars[key]):
                            dep_vars.pop(key)

        # filter out ELSI variants with -PEXSI suffix
        if dep == 'ELSI' and len(dep_vars) > 1:
            pexsi_vsuff_vars = [v for v in dep_vars.keys() if v.endswith('versionsuffix: -PEXSI')]
            if len(pexsi_vsuff_vars) == 1:
                dep_vars = dict((k, v) for (k, v) in dep_vars.items() if k != pexsi_vsuff_vars[0])

        # only single variant is always OK
        if len(dep_vars) == 1:
            res = True

        elif len(dep_vars) == 2 and dep in ['Python', 'Tkinter']:
            # for Python & Tkinter, it's OK to have on 2.x and one 3.x version
            v2_dep_vars = [x for x in dep_vars.keys() if x.startswith('version: 2.')]
            v3_dep_vars = [x for x in dep_vars.keys() if x.startswith('version: 3.')]
            if len(v2_dep_vars) == 1 and len(v3_dep_vars) == 1:
                res = True

        # two variants is OK if one is for Python 2.x and the other is for Python 3.x (based on versionsuffix)
        elif len(dep_vars) == 2:
            py2_dep_vars = [x for x in dep_vars.keys() if '; versionsuffix: -Python-2.' in x]
            py3_dep_vars = [x for x in dep_vars.keys() if '; versionsuffix: -Python-3.' in x]
            if len(py2_dep_vars) == 1 and len(py3_dep_vars) == 1:
                res = True

        return res

    def test_check_dep_vars(self):
        """Test check_dep_vars utility method."""

        # one single dep version: OK
        self.assertTrue(self.check_dep_vars('testdep', {
            'version: 1.2.3; versionsuffix:': ['foo-1.2.3.eb', 'bar-4.5.6.eb'],
        }))
        self.assertTrue(self.check_dep_vars('testdep', {
            'version: 1.2.3; versionsuffix: -test': ['foo-1.2.3.eb', 'bar-4.5.6.eb'],
        }))

        # two or more dep versions (no special case: not OK)
        self.assertFalse(self.check_dep_vars('testdep', {
            'version: 1.2.3; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 4.5.6; versionsuffix:': ['bar-4.5.6.eb'],
        }))
        self.assertFalse(self.check_dep_vars('testdep', {
            'version: 0.0; versionsuffix:': ['foobar-0.0.eb'],
            'version: 1.2.3; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 4.5.6; versionsuffix:': ['bar-4.5.6.eb'],
        }))

        # Java is a special case, with wrapped Java versions
        self.assertTrue(self.check_dep_vars('Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
        }))
        # two Java wrappers is not OK
        self.assertFalse(self.check_dep_vars('Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11.0.2; versionsuffix:': ['bar-4.5.6.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6.eb'],
        }))
        # OK to have two or more wrappers if versionsuffix is used to indicate exception
        self.assertTrue(self.check_dep_vars('Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11.0.2; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
        }))
        # versionsuffix must be there for all easyconfigs to indicate exception
        self.assertFalse(self.check_dep_vars('Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11.0.2; versionsuffix:': ['bar-4.5.6-Java-11.eb', 'bar-4.5.6.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6-Java-11.eb', 'bar-4.5.6.eb'],
        }))
        self.assertTrue(self.check_dep_vars('Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11.0.2; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
            'version: 12.1.6; versionsuffix:': ['foobar-0.0-Java-12.eb'],
            'version: 12; versionsuffix:': ['foobar-0.0-Java-12.eb'],
        }))

        # strange situation: odd number of Java versions
        # not OK: two Java wrappers (and no versionsuffix to indicate exception)
        self.assertFalse(self.check_dep_vars('Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6.eb'],
        }))
        # OK because of -Java-11 versionsuffix
        self.assertTrue(self.check_dep_vars('Java', {
            'version: 1.8.0_221; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
        }))
        # not OK: two Java wrappers (and no versionsuffix to indicate exception)
        self.assertFalse(self.check_dep_vars('Java', {
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11.0.2; versionsuffix:': ['bar-4.5.6.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6.eb'],
        }))
        # OK because of -Java-11 versionsuffix
        self.assertTrue(self.check_dep_vars('Java', {
            'version: 1.8; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 11.0.2; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
            'version: 11; versionsuffix:': ['bar-4.5.6-Java-11.eb'],
        }))

        # two different versions of Boost is not OK
        self.assertFalse(self.check_dep_vars('Boost', {
            'version: 1.64.0; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.70.0; versionsuffix:': ['foo-2.3.4.eb'],
        }))

        # a different Boost version that is only used as dependency for a matching Boost.Python is fine
        self.assertTrue(self.check_dep_vars('Boost', {
            'version: 1.64.0; versionsuffix:': ['Boost.Python-1.64.0-gompi-2019a.eb'],
            'version: 1.70.0; versionsuffix:': ['foo-2.3.4.eb'],
        }))
        self.assertTrue(self.check_dep_vars('Boost', {
            'version: 1.64.0; versionsuffix:': ['Boost.Python-1.64.0-gompi-2018b.eb'],
            'version: 1.66.0; versionsuffix:': ['Boost.Python-1.66.0-gompi-2019a.eb'],
            'version: 1.70.0; versionsuffix:': ['foo-2.3.4.eb'],
        }))
        self.assertFalse(self.check_dep_vars('Boost', {
            'version: 1.64.0; versionsuffix:': ['Boost.Python-1.64.0-gompi-2019a.eb'],
            'version: 1.66.0; versionsuffix:': ['foo-1.2.3.eb'],
            'version: 1.70.0; versionsuffix:': ['foo-2.3.4.eb'],
        }))

        self.assertTrue(self.check_dep_vars('Boost', {
            'version: 1.63.0; versionsuffix: -Python-2.7.14': ['EMAN2-2.21a-foss-2018a-Python-2.7.14-Boost-1.63.0.eb'],
            'version: 1.64.0; versionsuffix:': ['Boost.Python-1.64.0-gompi-2018a.eb'],
            'version: 1.66.0; versionsuffix:': ['BLAST+-2.7.1-foss-2018a.eb'],
        }))

        self.assertTrue(self.check_dep_vars('Boost', {
            'version: 1.64.0; versionsuffix:': [
                'Boost.Python-1.64.0-gompi-2019a.eb',
                'EMAN2-2.3-foss-2019a-Python-2.7.15.eb',
            ],
            'version: 1.70.0; versionsuffix:': [
                'BLAST+-2.9.0-gompi-2019a.eb',
                'Boost.Python-1.70.0-gompi-2019a.eb',
            ],
        }))

    def test_dep_versions_per_toolchain_generation(self):
        """
        Check whether there's only one dependency version per toolchain generation actively used.
        This is enforced to try and limit the chance of running into conflicts when multiple modules built with
        the same toolchain are loaded together.
        """
        if EasyConfigTest.ordered_specs is None:
            self.process_all_easyconfigs()

        ecs_by_full_mod_name = dict((ec['full_mod_name'], ec) for ec in EasyConfigTest.parsed_easyconfigs)
        if len(ecs_by_full_mod_name) != len(EasyConfigTest.parsed_easyconfigs):
            self.fail('Easyconfigs with duplicate full_mod_name found')

        # Cache already determined dependencies
        ec_to_deps = dict()

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

        # some software also follows <year>{a,b} versioning scheme,
        # which throws off the pattern matching done below for toolchain versions
        false_positives_regex = re.compile('^MATLAB-Engine-20[0-9][0-9][ab]')

        # restrict to checking dependencies of easyconfigs using common toolchains (start with 2018a)
        # and GCCcore subtoolchain for common toolchains, starting with GCCcore 7.x
        for pattern in ['201[89][ab]', '20[2-9][0-9][ab]', r'GCCcore-[7-9]\.[0-9]']:
            all_deps = {}
            regex = re.compile(r'^.*-(?P<tc_gen>%s).*\.eb$' % pattern)

            # collect variants for all dependencies of easyconfigs that use a toolchain that matches
            for ec in EasyConfigTest.ordered_specs:
                ec_file = os.path.basename(ec['spec'])

                # take into account software which also follows a <year>{a,b} versioning scheme
                ec_file = false_positives_regex.sub('', ec_file)

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
            multi_dep_vars, multi_dep_vars_msg = [], ''
            for tc_gen in sorted(all_deps.keys()):
                for dep in sorted(all_deps[tc_gen].keys()):
                    dep_vars = all_deps[tc_gen][dep]
                    if not self.check_dep_vars(dep, dep_vars):
                        multi_dep_vars.append(dep)
                        multi_dep_vars_msg += "\nfound %s variants of '%s' dependency " % (len(dep_vars), dep)
                        multi_dep_vars_msg += "in easyconfigs using '%s' toolchain generation\n* " % tc_gen
                        multi_dep_vars_msg += '\n* '.join("%s as dep for %s" % v for v in sorted(dep_vars.items()))
                        multi_dep_vars_msg += '\n'

            error_msg = "No multi-variant deps found for '%s' easyconfigs:\n%s" % (regex.pattern, multi_dep_vars_msg)
            self.assertFalse(multi_dep_vars, error_msg)

    def test_sanity_check_paths(self):
        """Make sure specified sanity check paths adher to the requirements."""

        if EasyConfigTest.ordered_specs is None:
            self.process_all_easyconfigs()

        for ec in EasyConfigTest.parsed_easyconfigs:
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
                    # only exception: TEMPLATE.eb
                    if not (dirpath.endswith('/easybuild/easyconfigs') and filenames == ['TEMPLATE.eb']):
                        self.assertTrue(False, "List of easyconfig files in %s is empty: %s" % (dirpath, filenames))

    def check_sha256_checksums(self, changed_ecs):
        """Make sure changed easyconfigs have SHA256 checksums in place."""

        # list of software for which checksums can not be required,
        # e.g. because 'source' files need to be constructed manually
        whitelist = ['Kent_tools-*', 'MATLAB-*', 'OCaml-*', 'OpenFOAM-Extend-4.1-*']

        # the check_sha256_checksums function (again) creates an EasyBlock instance
        # for easyconfigs using the Bundle easyblock, this is a problem because the 'sources' easyconfig parameter
        # is updated in place (sources for components are added the 'parent' sources) in Bundle's __init__;
        # therefore, we need to reset 'sources' to an empty list here if Bundle is used...
        # likewise for 'patches' and 'checksums'
        for ec in changed_ecs:
            if ec['easyblock'] in ['Bundle', 'PythonBundle']:
                ec['sources'] = []
                ec['patches'] = []
                ec['checksums'] = []

        # filter out deprecated easyconfigs
        retained_changed_ecs = []
        for ec in changed_ecs:
            if not ec['deprecated']:
                retained_changed_ecs.append(ec)

        checksum_issues = check_sha256_checksums(retained_changed_ecs, whitelist=whitelist)
        self.assertTrue(len(checksum_issues) == 0, "No checksum issues:\n%s" % '\n'.join(checksum_issues))

    def check_python_packages(self, changed_ecs, added_ecs_filenames):
        """Several checks for easyconfigs that install (bundles of) Python packages."""

        # These packages do not support installation with 'pip'
        whitelist_pip = [r'MATLAB-Engine-.*', r'PyTorch-.*', r'Meld-.*']

        whitelist_pip_check = [
            r'Mako-1.0.4.*Python-2.7.12.*',
            # no pip 9.x or newer for configparser easyconfigs using a 2016a or 2016b toolchain
            r'configparser-3.5.0.*-2016[ab].*',
        ]

        failing_checks = []

        for ec in changed_ecs:

            ec_fn = os.path.basename(ec.path)
            easyblock = ec.get('easyblock')
            exts_defaultclass = ec.get('exts_defaultclass')
            exts_default_options = ec.get('exts_default_options', {})

            download_dep_fail = ec.get('download_dep_fail')
            exts_download_dep_fail = ec.get('exts_download_dep_fail')
            use_pip = ec.get('use_pip') or exts_default_options.get('use_pip')

            # download_dep_fail should be set when using PythonPackage
            if easyblock == 'PythonPackage':
                if download_dep_fail is None:
                    failing_checks.append("'download_dep_fail' should be set in %s" % ec_fn)

            # use_pip should be set when using PythonPackage or PythonBundle (except for whitelisted easyconfigs)
            if easyblock in ['PythonBundle', 'PythonPackage']:
                if use_pip is None and not any(re.match(regex, ec_fn) for regex in whitelist_pip):
                    failing_checks.append("'use_pip' should be set in %s" % ec_fn)

            # download_dep_fail is enabled automatically in PythonBundle easyblock, so shouldn't be set
            if easyblock == 'PythonBundle':
                if download_dep_fail or exts_download_dep_fail:
                    fail = "'*download_dep_fail' should not be set in %s since PythonBundle easyblock is used" % ec_fn
                    failing_checks.append(fail)

            elif exts_defaultclass == 'PythonPackage':
                # bundle of Python packages should use PythonBundle
                if easyblock == 'Bundle':
                    fail = "'PythonBundle' easyblock should be used for bundle of Python packages in %s" % ec_fn
                    failing_checks.append(fail)
                else:
                    # both download_dep_fail and use_pip should be set via exts_default_options
                    # when installing Python packages as extensions
                    for key in ['download_dep_fail', 'use_pip']:
                        if exts_default_options.get(key) is None:
                            failing_checks.append("'%s' should be set in exts_default_options in %s" % (key, ec_fn))

            # if Python is a dependency, that should be reflected in the versionsuffix
            # Tkinter is an exception, since its version always matches the Python version anyway
            # Python 3.8.6 and later are also excluded, as we consider python 3 the default python
            # Also whitelist some updated versions of Amber
            whitelist_python_suffix = ['Amber-16-*-2018b-AmberTools-17-patchlevel-10-15.eb',
                                       'Amber-16-intel-2017b-AmberTools-17-patchlevel-8-12.eb']
            whitelisted = any(re.match(regex, ec_fn) for regex in whitelist_python_suffix)
            has_python_dep = any(dep['name'] == 'Python' for dep in ec['dependencies']
                                 if LooseVersion(dep['version']) < LooseVersion('3.8.6'))
            if has_python_dep and ec.name != 'Tkinter' and not whitelisted:
                if not re.search(r'-Python-[23]\.[0-9]+\.[0-9]+', ec['versionsuffix']):
                    msg = "'-Python-%%(pyver)s' should be included in versionsuffix in %s" % ec_fn
                    # This is only a failure for newly added ECs, not for existing ECS
                    # As that would probably break many ECs
                    if ec_fn in added_ecs_filenames:
                        failing_checks.append(msg)
                    else:
                        print('\nNote: Failed non-critical check: ' + msg)
            else:
                has_recent_python3_dep = any(dep['name'] == 'Python' for dep in ec['dependencies']
                                             if LooseVersion(dep['version']) >= LooseVersion('3.8.6'))
                if has_recent_python3_dep and re.search(r'-Python-3\.[0-9]+\.[0-9]+', ec['versionsuffix']):
                    msg = "'-Python-%%(pyver)s' should no longer be included in versionsuffix in %s" % ec_fn
                    failing_checks.append(msg)

            # require that running of "pip check" during sanity check is enabled via sanity_pip_check
            if use_pip and easyblock in ['PythonBundle', 'PythonPackage']:
                sanity_pip_check = ec.get('sanity_pip_check') or exts_default_options.get('sanity_pip_check')
                if not sanity_pip_check and not any(re.match(regex, ec_fn) for regex in whitelist_pip):
                    if not any(re.match(regex, ec_fn) for regex in whitelist_pip_check):
                        failing_checks.append("sanity_pip_check should be enabled in %s" % ec_fn)

        self.assertFalse(failing_checks, '\n'.join(failing_checks))

    def check_sanity_check_paths(self, changed_ecs):
        """Make sure a custom sanity_check_paths value is specified for easyconfigs that use a generic easyblock."""

        # GoPackage, PythonBundle & PythonPackage already have a decent customised sanity_check_paths
        # BuildEnv, ModuleRC and Toolchain easyblocks doesn't install anything so there is nothing to check.
        whitelist = ['BuildEnv', 'CrayToolchain', 'GoPackage', 'ModuleRC', 'PythonBundle', 'PythonPackage',
                     'Toolchain']
        # Bundles of dependencies without files of their own
        # Autotools: Autoconf + Automake + libtool, (recent) GCC: GCCcore + binutils, CUDA: GCC + CUDAcore,
        # CESM-deps: Python + Perl + netCDF + ESMF + git
        bundles_whitelist = ['Autotools', 'CESM-deps', 'CUDA', 'GCC']

        failing_checks = []

        for ec in changed_ecs:

            easyblock = ec.get('easyblock')

            if is_generic_easyblock(easyblock) and not ec.get('sanity_check_paths'):
                if easyblock in whitelist or (easyblock == 'Bundle' and ec['name'] in bundles_whitelist):
                    pass
                else:
                    ec_fn = os.path.basename(ec.path)
                    failing_checks.append("No custom sanity_check_paths found in %s" % ec_fn)

        self.assertFalse(failing_checks, '\n'.join(failing_checks))

    def check_https(self, changed_ecs):
        """Make sure https:// URL is used (if it exists) for homepage/source_urls (rather than http://)."""

        whitelist = [
            'Kaiju',  # invalid certificate at https://kaiju.binf.ku.dk
            'libxml2',  # https://xmlsoft.org works, but invalid certificate
            'p4vasp',  # https://www.p4vasp.at doesn't work
            'ITSTool',  # https://itstool.org/ doesn't work
            'UCX-',  # bad certificate for https://www.openucx.org
            'MUMPS',  # https://mumps.enseeiht.fr doesn't work
            'PyFR',  # https://www.pyfr.org doesn't work
            'PycURL',  # bad certificate for https://pycurl.io/
        ]
        url_whitelist = [
            # https:// doesn't work, results in index page being downloaded instead
            # (see https://github.com/easybuilders/easybuild-easyconfigs/issues/9692)
            'http://isl.gforge.inria.fr',
            # https:// leads to File Not Found
            'http://tau.uoregon.edu/',
        ]

        http_regex = re.compile('http://[^"\'\n]+', re.M)

        failing_checks = []
        for ec in changed_ecs:
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

                https_url = http_url.replace('http://', 'https://')
                try:
                    https_url_works = bool(urlopen(https_url, timeout=5))
                except Exception:
                    https_url_works = False

                if https_url_works:
                    failing_checks.append("Found http:// URL in %s, should be https:// : %s" % (ec_fn, http_url))

        self.assertFalse(failing_checks, '\n'.join(failing_checks))

    def test_changed_files_pull_request(self):
        """Specific checks only done for the (easyconfig) files that were changed in a pull request."""
        def get_eb_files_from_diff(diff_filter):

            # first determine the 'merge base' between target branch and PR branch
            # cfr. https://git-scm.com/docs/git-merge-base
            cmd = "git merge-base %s HEAD" % target_branch
            out, ec = run_cmd(cmd, simple=False, log_ok=False)
            if ec == 0:
                merge_base = out.strip()
                print("Merge base for %s and HEAD: %s" % (target_branch, merge_base))
            else:
                msg = "Failed to determine merge base (ec: %s, output: '%s'), "
                msg += "falling back to specifying target branch %s"
                print(msg % (ec, out, target_branch))
                merge_base = target_branch

            # determine list of changed files using 'git diff' and merge base determined above
            cmd = "git diff --name-only --diff-filter=%s %s..HEAD" % (diff_filter, merge_base)
            out, _ = run_cmd(cmd, simple=False)
            return [os.path.basename(f) for f in out.strip().split('\n') if f.endswith('.eb')]

        # $TRAVIS_PULL_REQUEST should be a PR number, otherwise we're not running tests for a PR
        travis_pr_test = re.match('^[0-9]+$', os.environ.get('TRAVIS_PULL_REQUEST', '(none)'))

        # when testing a PR in GitHub Actions, $GITHUB_EVENT_NAME will be set to 'pull_request'
        github_pr_test = os.environ.get('GITHUB_EVENT_NAME') == 'pull_request'

        if travis_pr_test or github_pr_test:

            # target branch should be anything other than 'master';
            # usually is 'develop', but could also be a release branch like '3.7.x'
            if travis_pr_test:
                target_branch = os.environ.get('TRAVIS_BRANCH', None)
            else:
                target_branch = os.environ.get('GITHUB_BASE_REF', None)

            if target_branch is None:
                self.assertTrue(False, "Failed to determine target branch for current pull request.")

            if target_branch != 'master':

                if not EasyConfigTest.parsed_easyconfigs:
                    self.process_all_easyconfigs()

                # relocate to top-level directory of repository to run 'git diff' command
                top_dir = os.path.dirname(os.path.dirname(get_paths_for('easyconfigs')[0]))
                cwd = change_dir(top_dir)

                # get list of changed easyconfigs
                changed_ecs_filenames = get_eb_files_from_diff(diff_filter='M')
                added_ecs_filenames = get_eb_files_from_diff(diff_filter='A')
                if changed_ecs_filenames:
                    print("\nList of changed easyconfig files in this PR: %s" % '\n'.join(changed_ecs_filenames))
                if added_ecs_filenames:
                    print("\nList of added easyconfig files in this PR: %s" % '\n'.join(added_ecs_filenames))

                change_dir(cwd)

                # grab parsed easyconfigs for changed easyconfig files
                changed_ecs = []
                for ec_fn in changed_ecs_filenames + added_ecs_filenames:
                    match = None
                    for ec in EasyConfigTest.parsed_easyconfigs:
                        if os.path.basename(ec['spec']) == ec_fn:
                            match = ec['ec']
                            break

                    if match:
                        changed_ecs.append(match)
                    else:
                        # if no easyconfig is found, it's possible some archived easyconfigs were touched in the PR...
                        # so as a last resort, try to find the easyconfig file in __archive__
                        easyconfigs_path = get_paths_for("easyconfigs")[0]
                        specs = glob.glob('%s/__archive__/*/*/%s' % (easyconfigs_path, ec_fn))
                        if len(specs) == 1:
                            ec = process_easyconfig(specs[0])[0]
                            changed_ecs.append(ec['ec'])
                        else:
                            error_msg = "Failed to find parsed easyconfig for %s" % ec_fn
                            error_msg += " (and could not isolate it in easyconfigs archive either)"
                            self.assertTrue(False, error_msg)

                # run checks on changed easyconfigs
                self.check_sha256_checksums(changed_ecs)
                self.check_python_packages(changed_ecs, added_ecs_filenames)
                self.check_sanity_check_paths(changed_ecs)
                self.check_https(changed_ecs)

    def test_zzz_cleanup(self):
        """Dummy test to clean up global temporary directory."""
        shutil.rmtree(self.TMPDIR)


def template_easyconfig_test(self, spec):
    """Tests for an individual easyconfig: parsing, instantiating easyblock, check patches, ..."""

    # set to False, so it's False in case of this test failing
    global single_tests_ok
    prev_single_tests_ok = single_tests_ok
    single_tests_ok = False

    # give recent EasyBuild easyconfigs special treatment
    # replace use deprecated dummy toolchain, required to avoid breaking "eb --install-latest-eb-release",
    # with SYSTEM toolchain constant
    ec_fn = os.path.basename(spec)
    if ec_fn == 'EasyBuild-3.9.4.eb' or ec_fn.startswith('EasyBuild-4.'):
        ectxt = read_file(spec)
        regex = re.compile('^toolchain = .*dummy.*', re.M)
        ectxt = regex.sub('toolchain = SYSTEM', ectxt)
        write_file(spec, ectxt)

    # parse easyconfig
    ecs = process_easyconfig(spec)
    if len(ecs) == 1:
        ec = ecs[0]['ec']

        # cache the parsed easyconfig, to avoid that it is parsed again
        EasyConfigTest.parsed_easyconfigs.append(ecs[0])
    else:
        self.assertTrue(False, "easyconfig %s does not contain blocks, yields only one parsed easyconfig" % spec)

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

    # instantiate easyblock with easyconfig file
    app_class = get_easyblock_class(easyblock, name=name)

    # check that automagic fallback to ConfigureMake isn't done (deprecated behaviour)
    fn = os.path.basename(spec)
    error_msg = "%s relies on automagic fallback to ConfigureMake, should use easyblock = 'ConfigureMake' instead" % fn
    self.assertTrue(easyblock or app_class is not ConfigureMake, error_msg)

    app = app_class(ec)

    # more sanity checks
    self.assertTrue(name, app.name)
    self.assertTrue(ec['version'], app.version)

    # make sure that deprecated 'dummy' toolchain is no longer used, should use 'system' toolchain instead
    error_msg_tmpl = "%s should use 'system' toolchain rather than deprecated 'dummy' toolchain"
    self.assertFalse(ec['toolchain']['name'] == 'dummy', error_msg_tmpl % os.path.basename(spec))

    # make sure that $root is not used, since it is not compatible with module files in Lua syntax
    res = re.findall(r'.*\$root.*', ec.rawtxt, re.M)
    error_msg = "Found use of '$root', not compatible with modules in Lua syntax, use '%%(installdir)s' instead: %s"
    self.assertFalse(res, error_msg % res)

    # check for redefined easyconfig parameters, there should be none...
    param_def_regex = re.compile(r'^(?P<key>\w+)\s*=', re.M)
    keys = param_def_regex.findall(ec.rawtxt)
    redefined_keys = []
    for key in sorted(nub(keys)):
        cnt = keys.count(key)
        if cnt > 1:
            redefined_keys.append((key, cnt))

    redefined_keys_error_msg = "There should be no redefined easyconfig parameters, found %d: " % len(redefined_keys)
    redefined_keys_error_msg += ', '.join('%s (%d)' % x for x in redefined_keys)

    self.assertFalse(redefined_keys, redefined_keys_error_msg)

    # make sure old GitHub urls for EasyBuild that include 'hpcugent' are no longer used
    old_urls = [
        'github.com/hpcugent/easybuild',
        'hpcugent.github.com/easybuild',
        'hpcugent.github.io/easybuild',
    ]
    for old_url in old_urls:
        self.assertFalse(old_url in ec.rawtxt, "Old URL '%s' not found in %s" % (old_url, spec))

    # make sure binutils is included as a (build) dep if toolchain is GCCcore
    if ec['toolchain']['name'] == 'GCCcore':
        # with 'Tarball' easyblock: only unpacking, no building; Eigen is also just a tarball
        requires_binutils = ec['easyblock'] not in ['Tarball'] and ec['name'] not in ['Eigen']

        # let's also exclude the very special case where the system GCC is used as GCCcore, and only apply this
        # exception to the dependencies of binutils (since we should eventually build a new binutils with GCCcore)
        if ec['toolchain']['version'] == 'system':
            binutils_complete_dependencies = ['M4', 'Bison', 'flex', 'help2man', 'zlib', 'binutils']
            requires_binutils &= bool(ec['name'] not in binutils_complete_dependencies)

        # if no sources/extensions/components are specified, it's just a bundle (nothing is being compiled)
        requires_binutils &= bool(ec['sources'] or ec['exts_list'] or ec.get('components'))

        if requires_binutils:
            # dependencies() returns both build and runtime dependencies
            # in some cases, binutils can also be a runtime dep (e.g. for Clang)
            dep_names = [d['name'] for d in ec.dependencies()]
            self.assertTrue('binutils' in dep_names, "binutils is a build dep in %s: %s" % (spec, dep_names))

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
    extra_opts = app.extra_options()
    for key in extra_opts:
        self.assertTrue(key in app.cfg)

    app.close_log()
    os.remove(app.logfile)

    # dump the easyconfig file
    handle, test_ecfile = tempfile.mkstemp()
    os.close(handle)

    ec.dump(test_ecfile)
    dumped_ec = EasyConfigParser(test_ecfile).get_config_dict()
    os.remove(test_ecfile)

    # inject dummy values for templates that are only known at a later stage
    dummy_template_values = {
        'builddir': '/dummy/builddir',
        'installdir': '/dummy/installdir',
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

        orig_val = resolve_template(ec_dict[key], ec.template_values)
        dumped_val = resolve_template(dumped_ec[key], ec.template_values)

        # take into account that dumped value for *dependencies may include hard-coded subtoolchains
        # if no easyconfig was found for the dependency with the 'parent' toolchain,
        # if may get resolved using a subtoolchain, which is then hardcoded in the dumped easyconfig
        if key in DEPENDENCY_PARAMETERS:
            # number of dependencies should remain the same
            self.assertEqual(len(orig_val), len(dumped_val))
            for orig_dep, dumped_dep in zip(orig_val, dumped_val):
                # name should always match
                self.assertEqual(orig_dep[0], dumped_dep[0])

                # version should always match, or be a possibility from the version dict
                if isinstance(orig_dep[1], dict):
                    self.assertTrue(dumped_dep[1] in orig_dep[1].values())
                else:
                    self.assertEqual(orig_dep[1], dumped_dep[1])

                # 3rd value is versionsuffix;
                if len(dumped_dep) >= 3:
                    # if no versionsuffix was specified in original dep spec, then dumped value should be empty string
                    if len(orig_dep) >= 3:
                        self.assertEqual(dumped_dep[2], orig_dep[2])
                    else:
                        self.assertEqual(dumped_dep[2], '')

                # 4th value is toolchain spec
                if len(dumped_dep) >= 4:
                    if len(orig_dep) >= 4:
                        self.assertEqual(dumped_dep[3], orig_dep[3])
                    else:
                        # if a subtoolchain is specifed (only) in the dumped easyconfig,
                        # it should *not* be the same as the parent toolchain
                        self.assertNotEqual(dumped_dep[3], (orig_toolchain['name'], orig_toolchain['version']))

        # take into account that for some string-valued easyconfig parameters (configopts & co),
        # the easyblock may have injected additional values, which affects the dumped easyconfig file
        elif isinstance(orig_val, string_type):
            error_msg = "%s value '%s' should start with '%s'" % (key, dumped_val, orig_val)
            self.assertTrue(dumped_val.startswith(orig_val), error_msg)
        else:
            self.assertEqual(orig_val, dumped_val)

    # test passed, so set back to True
    single_tests_ok = True and prev_single_tests_ok


def suite():
    """Return all easyblock initialisation tests."""
    def make_inner_test(spec_path):
        def innertest(self):
            template_easyconfig_test(self, spec_path)
        return innertest

    # dynamically generate a separate test for each of the available easyconfigs
    # define new inner functions that can be added as class methods to InitTest
    easyconfigs_path = get_paths_for('easyconfigs')[0]
    cnt = 0
    for (subpath, _, specs) in os.walk(easyconfigs_path, topdown=True):

        # ignore archived easyconfigs
        if '__archive__' in subpath:
            continue

        for spec in specs:
            if spec.endswith('.eb') and spec != 'TEMPLATE.eb':
                cnt += 1
                innertest = make_inner_test(os.path.join(subpath, spec))
                innertest.__doc__ = "Test for parsing of easyconfig %s" % spec
                # double underscore so parsing tests are run first
                innertest.__name__ = "test__parse_easyconfig_%s" % spec
                setattr(EasyConfigTest, innertest.__name__, innertest)

    print("Found %s easyconfigs..." % cnt)
    return TestLoader().loadTestsFromTestCase(EasyConfigTest)


if __name__ == '__main__':
    main()
