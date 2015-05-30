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
General unit tests for the easybuild-easyblocks repo.

@author: Kenneth Hoste (Ghent University)
"""
import os
import re
import shutil
import tempfile
from unittest import TestLoader, main
from vsc.utils.testing import EnhancedTestCase

from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


EASYBLOCK_BODY = """
from easybuild.framework.easyblock import EasyBlock
class EB_%s(EasyBlock):
    pass
"""
EASYBLOCKS_FLATTEN_EXTEND_PATH = """
subdirs = [chr(l) for l in range(ord('a'), ord('z') + 1)] + ['0']
for subdir in subdirs:
    __path__ = extend_path(__path__, '%s.%s' % (__name__, subdir))
"""
NAMESPACE_EXTEND_PATH = "from pkgutil import extend_path; __path__ = extend_path(__path__, __name__)"


def det_path_for_import(module, pythonpath=None):
    """Determine filepath obtained when importing specified module."""
    cmd_tmpl = "python -c 'import %(mod)s; print %(mod)s.__file__'"

    if pythonpath:
        cmd_tmpl = "PYTHONPATH=%s:$PYTHONPATH %s" % (pythonpath, cmd_tmpl)

    cmd = cmd_tmpl % {'mod': module}

    out, _ = run_cmd(cmd, simple=False)

    # only return last line that should contain path to imported module
    # warning messages may precede it
    return out.strip().split('\n')[-1]


def up(path, level):
    """Determine parent path for given path, N levels up."""
    while level:
        path = os.path.dirname(path)
        level -= 1
    return path


class GeneralEasyblockTest(EnhancedTestCase):
    """General easybuild-easyblocks tests."""

    def setUp(self):
        """Test setup."""
        super(GeneralEasyblockTest, self).setUp()
        self.tmpdir = tempfile.mkdtemp()
        self.cwd = os.getcwd()

    def tearDown(self):
        """Test cleanup."""
        super(GeneralEasyblockTest, self).tearDown()
        os.chdir(self.cwd)
        shutil.rmtree(self.tmpdir)

    def test_custom_easyblocks_repo(self):
        """Test whether using a custom easyblocks repo works as expected."""
        easyblocks_repo_path = up(os.path.abspath(__file__), 3)

        # prepend path to easybuild-easyblocks repo to $PYTHONPATH, so we're in full(?) control
        pythonpaths = os.environ['PYTHONPATH'].split(os.pathsep)
        os.environ['PYTHONPATH'] = os.pathsep.join([easyblocks_repo_path] + pythonpaths)

        # set up custom easyblocks repo
        custom_easyblocks_repo_path = os.path.join(self.tmpdir, 'myeasyblocks')
        os.makedirs(os.path.join(custom_easyblocks_repo_path, 'easybuild', 'easyblocks'))

        def write_module(path, txt):
            """Write provided contents to module at given path in custom easyblocks repo."""
            handle = open(os.path.join(custom_easyblocks_repo_path, 'easybuild', path), 'w')
            handle.write(txt)
            handle.close()

        # this test should be run out of the easyblocks repository,
        # to avoid that the working directory that is prepended to the Python search path affects the test results
        os.chdir(self.tmpdir)

        eb_easyblocks = [
            ('easybuild.easyblocks', 3),  # easybuild.easyblocks.__init__.py
            ('easybuild.easyblocks.gcc', 4),  # easybuild.easyblocks.g.gcc.py
            # note: R easyblock is a special case, due to clash with 'easybuild.easyblocks.r' namespace
            ('easybuild.easyblocks.r', 4),  # easybuild.easyblocks.r.__init__.py
        ]
        for (mod, depth) in eb_easyblocks:
            res = det_path_for_import(mod)
            parent_path = up(res, depth)
            msg = "parent path for '%s' module %s == %s" % (mod, parent_path, easyblocks_repo_path)
            self.assertTrue(os.path.samefile(easyblocks_repo_path, parent_path), msg)

        # importing EB_R class from easybuild.easyblocks.r works fine
        run_cmd("python -c 'from easybuild.easyblocks.r import EB_R'")

        # importing a non-existing module fails
        err_msg = "No module named .*"
        self.assertErrorRegex(EasyBuildError, err_msg, det_path_for_import, 'easybuild.easyblocks.nosuchsoftwarefoobar')

        # define easybuild.easyblocks namespace in custom easyblocks repo
        write_module('__init__.py', NAMESPACE_EXTEND_PATH)
        txt = '\n'.join([NAMESPACE_EXTEND_PATH, EASYBLOCKS_FLATTEN_EXTEND_PATH])
        write_module(os.path.join('easyblocks', '__init__.py'), txt)

        # add custom easyblock for foobar
        write_module(os.path.join('easyblocks', 'foobar.py'), EASYBLOCK_BODY % 'foobar')

        # test importing from both easyblocks repos
        easyblocks = eb_easyblocks + [('easybuild.easyblocks.foobar', 3)]
        repo_paths = [
            custom_easyblocks_repo_path,  # easybuild.easyblocks is now initialised via custom easyblocks repo
            easyblocks_repo_path,  # GCC easyblock
            easyblocks_repo_path,  # R easyblock/package
            custom_easyblocks_repo_path,  # foobar easyblock
        ]
        for (mod, depth), repo_path in zip(easyblocks, repo_paths):
            res = det_path_for_import(mod, pythonpath=custom_easyblocks_repo_path)
            parent_path = up(res, depth)
            msg = "parent path for '%s' module %s == %s" % (mod, parent_path, repo_path)
            self.assertTrue(os.path.samefile(repo_path, parent_path), msg)

        # importing EB_R class from easybuild.easyblocks.r still works fine
        run_cmd("python -c 'from easybuild.easyblocks.r import EB_R'")

        # custom easyblocks override existing easyblocks (with custom easyblocks repo first in $PYTHONPATH)
        for software in ['GCC', 'R']:
            write_module(os.path.join('easyblocks', '%s.py' % software.lower()), EASYBLOCK_BODY % software)
            mod = 'easybuild.easyblocks.%s' % software.lower()
            res = det_path_for_import(mod, pythonpath=custom_easyblocks_repo_path)
            parent_path = up(res, 3)
            msg = "parent path for '%s' module %s == %s" % (mod, parent_path, custom_easyblocks_repo_path)
            self.assertTrue(os.path.samefile(custom_easyblocks_repo_path, parent_path), msg)

        # importing EB_R class from easybuild.easyblocks.r still works fine
        run_cmd("python -c 'from easybuild.easyblocks.r import EB_R'")

def suite():
    """Return all general easybuild-easyblocks tests."""
    return TestLoader().loadTestsFromTestCase(GeneralEasyblockTest)

if __name__ == '__main__':
    main()
