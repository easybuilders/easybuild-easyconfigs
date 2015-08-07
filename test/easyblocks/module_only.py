##
# Copyright 2015-2015 Ghent University
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
Unit tests to check that easyblocks are compatible with --module-only.

@author: Kenneth Hoste (Ghent University)
"""

import glob
import os
import re
import tempfile
from vsc.utils import fancylogger
from unittest import TestLoader, main
from vsc.utils.patterns import Singleton
from vsc.utils.testing import EnhancedTestCase

from easybuild.framework.easyconfig import easyconfig
import easybuild.tools.module_naming_scheme.toolchain as mns_toolchain
import easybuild.tools.options as eboptions
import easybuild.tools.toolchain.utilities as tc_utils
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import MANDATORY
from easybuild.framework.easyconfig.easyconfig import EasyConfig, get_easyblock_class
from easybuild.framework.easyconfig.tools import get_paths_for
from easybuild.tools import config
from easybuild.tools.filetools import write_file
from easybuild.tools.module_naming_scheme import GENERAL_CLASS


TMPDIR = tempfile.gettempdir()


def cleanup():
    """Perform cleanup of singletons and caches."""
    # clear Singelton instances, to start afresh
    Singleton._instances.clear()

    # empty caches
    tc_utils._initial_toolchain_instances.clear()
    easyconfig._easyconfigs_cache.clear()
    easyconfig._easyconfig_files_cache.clear()
    mns_toolchain._toolchain_details_cache.clear()


class ModuleOnlyTest(EnhancedTestCase):
    """ Baseclass for easyblock testcases """

    def writeEC(self, easyblock, name='foo', version='1.3.2', extratxt=''):
        """ create temporary easyconfig file """
        txt = '\n'.join([
            'easyblock = "%s"',
            'name = "%s"' % name,
            'version = "%s"' % version,
            'homepage = "http://example.com"',
            'description = "Dummy easyconfig file."',
            "toolchain = {'name': 'dummy', 'version': 'dummy'}",
            'sources = []',
            extratxt,
        ])

        write_file(self.eb_file, txt % easyblock)

    def setUp(self):
        """Setup test."""
        self.log = fancylogger.getLogger("EasyblocksModuleOnlyTest", fname=False)
        fd, self.eb_file = tempfile.mkstemp(prefix='easyblocks_module_only_test_', suffix='.eb')
        os.close(fd)

    def tearDown(self):
        """Cleanup."""
        try:
            os.remove(self.eb_file)
        except OSError, err:
            self.log.error("Failed to remove %s: %s", self.eb_file, err)


def template_module_only_test(self, easyblock, name='foo', version='1.3.2'):
    """Test whether all easyblocks are compatible with --module-only."""

    class_regex = re.compile("^class (.*)\(.*", re.M)

    self.log.debug("easyblock: %s" % easyblock)

    # read easyblock Python module
    f = open(easyblock, "r")
    txt = f.read()
    f.close()

    # obtain easyblock class name using regex
    res = class_regex.search(txt)
    if res:
        ebname = res.group(1)
        self.log.debug("Found class name for easyblock %s: %s" % (easyblock, ebname))

        # figure out list of mandatory variables, and define with dummy values as necessary
        app_class = get_easyblock_class(ebname)

        # extend easyconfig to make sure mandatory custom easyconfig paramters are defined
        extra_options = app_class.extra_options()
        extra_txt = ''
        for (key, val) in extra_options.items():
            if val[2] == MANDATORY:
                extra_txt += '%s = "foo"\n' % key

        # write easyconfig file
        self.writeEC(ebname, name=name, version=version, extratxt=extra_txt)

        # initialize easyblock
        # if this doesn't fail, the test succeeds
        app = app_class(EasyConfig(self.eb_file))

        # run all steps, most should be skipped
        orig_workdir = os.getcwd()
        try:
            app.run_all_steps(run_test_cases=False)
        finally:
            os.chdir(orig_workdir)

        modfile = os.path.join(TMPDIR, 'modules', 'all', 'foo', '1.3.2')
        self.assertTrue(os.path.exists(modfile), "Module file %s was generated" % modfile)

        # cleanup
        app.close_log()
        os.remove(app.logfile)
    else:
        self.assertTrue(False, "Class found in easyblock %s" % easyblock)

def suite():
    """Return all easyblock --module-only tests."""
    # initialize configuration (required for e.g. default modules_tool setting)
    cleanup()
    eb_go = eboptions.parse_options(args=['--prefix=%s' % TMPDIR])
    config.init(eb_go.options, eb_go.get_options_by_section('config'))
    build_options = {
        # enable --force --module-only
        'force': True,
        'module_only': True,
        'silent': True,
        'suffix_modules_path': GENERAL_CLASS,
        'valid_module_classes': config.module_classes(),
        'valid_stops': [x[0] for x in EasyBlock.get_steps()],
    }
    config.init_build_options(build_options=build_options)
    config.set_tmpdir()

    # dynamically generate a separate test for each of the available easyblocks
    easyblocks_path = get_paths_for("easyblocks")[0]
    all_pys = glob.glob('%s/*/*.py' % easyblocks_path)
    easyblocks = [eb for eb in all_pys if os.path.basename(eb) != '__init__.py' and '/test/' not in eb]

    # filter out no longer supported easyblocks, or easyblocks that are tested in a different way
    excluded_easyblocks = ['versionindependendpythonpackage.py']
    easyblocks = [e for e in easyblocks if os.path.basename(e) not in excluded_easyblocks]

    for easyblock in easyblocks:
        # dynamically define new inner functions that can be added as class methods to ModuleOnlyTest
        if os.path.basename(easyblock) == 'systemcompiler.py':
            # use GCC as name when testing SystemCompiler easyblock
            exec("def innertest(self): template_module_only_test(self, '%s', name='GCC', version='system')" % easyblock)
        else:
            exec("def innertest(self): template_module_only_test(self, '%s')" % easyblock)
        innertest.__doc__ = "Test for using --module-only with easyblock %s" % easyblock
        innertest.__name__ = "test_easyblock_%s" % '_'.join(easyblock.replace('.py', '').split('/'))
        setattr(ModuleOnlyTest, innertest.__name__, innertest)

    return TestLoader().loadTestsFromTestCase(ModuleOnlyTest)

if __name__ == '__main__':
    main()
