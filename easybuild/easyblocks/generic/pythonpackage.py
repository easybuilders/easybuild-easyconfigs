##
# Copyright 2009-2013 Ghent University
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
EasyBuild support for Python packages, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os
import tempfile
from os.path import expanduser
from vsc import fancylogger

import easybuild.tools.environment as env
from easybuild.easyblocks.python import EXTS_FILTER_PYTHON_PACKAGES
from easybuild.framework.easyconfig import CUSTOM
from easybuild.framework.extensioneasyblock import ExtensionEasyBlock
from easybuild.tools.filetools import mkdir, rmtree2, run_cmd
from easybuild.tools.modules import get_software_version


def det_pylibdir():
    """Determine Python library directory."""
    log = fancylogger.getLogger('det_pylibdir', fname=False)
    pyver = get_software_version('Python')
    if not pyver:
        log.error("Python module not loaded.")
    else:
        # determine Python lib dir via distutils
        # use run_cmd, we can to talk to the active Python, not the system Python running EasyBuild
        prefix = '/tmp/'
        pycmd = 'import distutils.sysconfig; print(distutils.sysconfig.get_python_lib(prefix="%s"))' % prefix
        cmd = "python -c '%s'" % pycmd
        out, ec = run_cmd(cmd, simple=False)
        out = out.strip()

        # value obtained should start with specified prefix, otherwise something is very wrong
        if not out.startswith(prefix):
            tup = (cmd, prefix, out, ec)
            log.error("Output of %s does not start with specified prefix %s: %s (exit code %s)" % tup)

        pylibdir = out.strip()[len(prefix):]
        log.debug("Determined pylibdir using '%s': %s" % (cmd, pylibdir))
        return pylibdir


class PythonPackage(ExtensionEasyBlock):
    """Builds and installs a Python package, and provides a dedicated module file."""

    @staticmethod
    def extra_options():
        """Easyconfig parameters specific to Python packages."""
        extra_vars = {
            'runtest': [True, "Run unit tests.", CUSTOM],  # overrides default
        }
        return ExtensionEasyBlock.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Initialize custom class variables."""
        super(PythonPackage, self).__init__(*args, **kwargs)

        self.sitecfg = None
        self.sitecfgfn = 'site.cfg'
        self.sitecfglibdir = None
        self.sitecfgincdir = None
        self.testinstall = False
        self.testcmd = None
        self.unpack_options = ''

        self.pylibdir = None

        # make sure there's no site.cfg in $HOME, because setup.py will find it and use it
        if os.path.exists(os.path.join(expanduser('~'), 'site.cfg')):
            self.log.error('Found site.cfg in your home directory (%s), please remove it.' % expanduser('~'))

        if not 'modulename' in self.options:
            self.options['modulename'] = self.name.lower()

    def prepare_step(self):
        """Prepare easyblock by determining Python site lib dir."""
        super(PythonPackage, self).prepare_step()
        if not self.pylibdir:
            self.pylibdir = det_pylibdir()

    def prerun(self):
        """Prepare extension by determining Python site lib dir."""
        super(PythonPackage, self).prerun()
        self.pylibdir = det_pylibdir()

    def configure_step(self):
        """Configure Python package build."""

        if not self.pylibdir:
            self.log.error('Python module not loaded.')
        self.log.debug("Python library dir: %s" % self.pylibdir)

        if self.sitecfg is not None:
            # used by some extensions, like numpy, to find certain libs

            finaltxt = self.sitecfg
            if self.sitecfglibdir:
                repl = self.sitecfglibdir
                finaltxt = finaltxt.replace('SITECFGLIBDIR', repl)

            if self.sitecfgincdir:
                repl = self.sitecfgincdir
                finaltxt = finaltxt.replace('SITECFGINCDIR', repl)

            self.log.debug("Using %s: %s" % (self.sitecfgfn, finaltxt))
            try:
                if os.path.exists(self.sitecfgfn):
                    txt = open(self.sitecfgfn).read()
                    self.log.debug("Found %s: %s" % (self.sitecfgfn, txt))
                config = open(self.sitecfgfn, 'w')
                config.write(finaltxt)
                config.close()
            except IOError:
                self.log.exception("Creating %s failed" % self.sitecfgfn)

        # creates log entries for python being used, for debugging
        run_cmd("python -V")
        run_cmd("which python")
        run_cmd("python -c 'import sys; print(sys.executable)'")

    def build_step(self):
        """Build Python package using setup.py"""

        cmd = "python setup.py build %s" % self.cfg['makeopts']
        run_cmd(cmd, log_all=True, simple=True)

    def test_step(self):
        """Test the built Python package."""

        if isinstance(self.cfg['runtest'], basestring):
            self.testcmd = self.cfg['runtest']

        if self.cfg['runtest'] and not self.testcmd is None:
            extrapath = ""
            testinstalldir = None

            if self.testinstall:
                # install in test directory and export PYTHONPATH

                try:
                    testinstalldir = tempfile.mkdtemp()
                    mkdir(os.path.join(testinstalldir, self.pylibdir), parents=True)
                except OSError, err:
                    self.log.error("Failed to create test install dir: %s" % err)

                tup = (self.cfg['preinstallopts'], testinstalldir, self.cfg['installopts'])
                cmd = "%s python setup.py install --prefix=%s %s" % tup
                run_cmd(cmd, log_all=True, simple=True)

                run_cmd("python -c 'import sys; print(sys.path)'")  # print Python search path (debug)
                extrapath = "export PYTHONPATH=%s:$PYTHONPATH && " % os.path.join(testinstalldir, self.pylibdir)

            if self.testcmd:
                cmd = "%s%s" % (extrapath, self.testcmd)
                run_cmd(cmd, log_all=True, simple=True)

            if testinstalldir:
                try:
                    rmtree2(testinstalldir)
                except OSError, err:
                    self.log.exception("Removing testinstalldir %s failed: %s" % (testinstalldir, err))

    def install_step(self):
        """Install Python package to a custom path using setup.py"""

        # create expected directories
        abs_pylibdir = os.path.join(self.installdir, self.pylibdir)
        mkdir(abs_pylibdir, parents=True)

        # set PYTHONPATH as expected
        pythonpath = os.getenv('PYTHONPATH')
        env.setvar('PYTHONPATH', ":".join([x for x in [abs_pylibdir, pythonpath] if x is not None]))

        # actually install Python package
        tup = (self.cfg['preinstallopts'], self.installdir, self.cfg['installopts'])
        cmd = "%s python setup.py install --prefix=%s %s" % tup
        run_cmd(cmd, log_all=True, simple=True)

        # restore PYTHONPATH if it was set
        if pythonpath is not None:
            env.setvar('PYTHONPATH', pythonpath)

    def run(self):
        """Perform the actual Python package build/installation procedure"""

        if not self.src:
            self.log.error("No source found for Python package %s, required for installation. (src: %s)" % (self.name,
                                                                                                            self.src))
        super(PythonPackage, self).run(unpack_src=True)

        # configure, build, test, install
        self.configure_step()
        self.build_step()
        self.test_step()
        self.install_step()

    def sanity_check_step(self, *args, **kwargs):
        """
        Custom sanity check for Python packages
        """
        if not 'exts_filter' in kwargs:
            kwargs.update({'exts_filter': EXTS_FILTER_PYTHON_PACKAGES})
        return super(PythonPackage, self).sanity_check_step(*args, **kwargs)

    def make_module_extra(self):
        """Add install path to PYTHONPATH"""

        txt = self.moduleGenerator.prepend_paths("PYTHONPATH", [self.pylibdir])
        return super(PythonPackage, self).make_module_extra(txt)
