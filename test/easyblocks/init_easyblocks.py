##
# Copyright 2013-2015 Ghent University
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
Unit tests for initializing easyblocks.

@author: Kenneth Hoste (Ghent University)
"""

import glob
import os
import re
import tempfile
from vsc.utils import fancylogger
from unittest import TestCase, TestLoader, main

import easybuild.tools.options as eboptions
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import MANDATORY
from easybuild.framework.easyconfig.easyconfig import EasyConfig, get_easyblock_class
from easybuild.framework.easyconfig.tools import get_paths_for
from easybuild.tools import config
from easybuild.tools.filetools import write_file
from easybuild.tools.module_naming_scheme import GENERAL_CLASS
from easybuild.tools.run import parse_log_for_error, run_cmd, run_cmd_qa
from easybuild.tools.environment import modify_env, read_environment


class InitTest(TestCase):
    """ Baseclass for easyblock testcases """

    # initialize configuration (required for e.g. default modules_tool setting)
    eb_go = eboptions.parse_options()
    config.init(eb_go.options, eb_go.get_options_by_section('config'))
    build_options = {
        'suffix_modules_path': GENERAL_CLASS,
        'valid_module_classes': config.module_classes(),
        'valid_stops': [x[0] for x in EasyBlock.get_steps()],
    }
    config.init_build_options(build_options=build_options)
    config.set_tmpdir()
    del eb_go

    def writeEC(self, easyblock, name='foo', version='1.3.2', extratxt=''):
        """ create temporary easyconfig file """
        txt = '\n'.join([
            'easyblock = "%s"',
            'name = "%s"' % name,
            'version = "%s"' % version,
            'homepage = "http://example.com"',
            'description = "Dummy easyconfig file."',
            'toolchain = {"name": "dummy", "version": "dummy"}',
            'sources = []',
            extratxt,
        ])

        write_file(self.eb_file, txt % easyblock)

    def setUp(self):
        """Setup test."""
        self.log = fancylogger.getLogger("EasyblocksInitTest", fname=False)
        fd, self.eb_file = tempfile.mkstemp(prefix='easyblocks_init_test_', suffix='.eb')
        os.close(fd)

    def tearDown(self):
        """Cleanup."""
        try:
            os.remove(self.eb_file)
        except OSError, err:
            self.log.error("Failed to remove %s: %s" % (self.eb_file, err))


def template_init_test(self, easyblock, name='foo', version='1.3.2'):
    """Test whether all easyblocks can be initialized."""

    def check_extra_options_format(extra_options):
        """Make sure extra_options value is of correct format."""
        # EasyBuild v2.0: dict with <string> keys and <list> values
        self.assertTrue(isinstance(extra_options, dict))
        extra_options.items()
        extra_options.keys()
        extra_options.values()
        for key in extra_options.keys():
            self.assertTrue(isinstance(extra_options[key], list))
            self.assertTrue(len(extra_options[key]), 3)

    class_regex = re.compile("^class (.*)\(.*", re.M)

    self.log.debug("easyblock: %s" % easyblock)

    # read easyblock Python module
    f = open(easyblock, "r")
    txt = f.read()
    f.close()

    # make sure error reporting is done correctly (no more log.error, log.exception)
    log_method_regexes = [
        re.compile(r"log\.error\("),
        re.compile(r"log\.exception\("),
        re.compile(r"log\.raiseException\("),
    ]
    for regex in log_method_regexes:
        self.assertFalse(regex.search(txt), "No match for '%s' in %s" % (regex.pattern, easyblock))

    # obtain easyblock class name using regex
    res = class_regex.search(txt)
    if res:
        ebname = res.group(1)
        self.log.debug("Found class name for easyblock %s: %s" % (easyblock, ebname))

        # figure out list of mandatory variables, and define with dummy values as necessary
        app_class = get_easyblock_class(ebname)
        extra_options = app_class.extra_options()
        print easyblock, app_class, extra_options.keys()
        check_extra_options_format(extra_options)

        # extend easyconfig to make sure mandatory custom easyconfig paramters are defined
        extra_txt = ''
        for (key, val) in extra_options.items():
            if val[2] == MANDATORY:
                extra_txt += '%s = "foo"\n' % key

        # write easyconfig file
        self.writeEC(ebname, name=name, version=version, extratxt=extra_txt)

        # initialize easyblock
        # if this doesn't fail, the test succeeds
        app = app_class(EasyConfig(self.eb_file))

        # check whether easyblock instance is still using functions from a deprecated location
        mod = __import__(app.__module__, [], [], ['easybuild.easyblocks'])
        moved_functions = ['modify_env', 'parse_log_for_error', 'read_environment', 'run_cmd', 'run_cmd_qa']
        for fn in moved_functions:
            if hasattr(mod, fn):
                tup = (fn, app.__module__, globals()[fn].__module__)
                self.assertTrue(getattr(mod, fn) is globals()[fn], "%s in %s is imported from %s" % tup)
        renamed_functions = [
            ('source_paths', 'source_path'),
            ('get_avail_core_count', 'get_core_count'),
            ('get_os_type', 'get_kernel_name'),
            ('det_full_ec_version', 'det_installversion'),
        ]
        for (new_fn, old_fn) in renamed_functions:
            self.assertFalse(hasattr(mod, old_fn), "%s: %s is replaced by %s" % (app.__module__, old_fn, new_fn))

        # cleanup
        app.close_log()
        os.remove(app.logfile)
    else:
        self.assertTrue(False, "Class found in easyblock %s" % easyblock)


def suite():
    """Return all easyblock initialisation tests."""

    # dynamically generate a separate test for each of the available easyblocks
    easyblocks_path = get_paths_for("easyblocks")[0]
    all_pys = glob.glob('%s/*/*.py' % easyblocks_path)
    easyblocks = [eb for eb in all_pys if not eb.endswith('__init__.py') and not '/test/' in eb]

    for easyblock in easyblocks:
        # dynamically define new inner functions that can be added as class methods to InitTest
        if os.path.basename(easyblock) == 'systemcompiler.py':
            # use GCC as name when testing SystemCompiler easyblock
            exec("def innertest(self): template_init_test(self, '%s', name='GCC', version='system')" % easyblock)
        else:
            exec("def innertest(self): template_init_test(self, '%s')" % easyblock)

        innertest.__doc__ = "Test for initialisation of easyblock %s" % easyblock
        innertest.__name__ = "test_easyblock_%s" % '_'.join(easyblock.replace('.py', '').split('/'))
        setattr(InitTest, innertest.__name__, innertest)

    return TestLoader().loadTestsFromTestCase(InitTest)

if __name__ == '__main__':
    main()
