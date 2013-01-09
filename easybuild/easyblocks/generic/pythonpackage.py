# #
# Copyright 2009-2013 Ghent University
# Copyright 2009-2013 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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
# #
"""
EasyBuild support for Python packages, implemented as an easyblock
"""
import os

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import run_cmd, mkdir
from easybuild.tools.modules import get_software_version


class PythonPackage(EasyBlock):
    """Builds and installs a Python package, and provides a dedicated module file."""

    def __init__(self, *args, **kwargs):
        """Initialize custom variables."""
        super(PythonPackage, self).__init__(*args, **kwargs)

        # template for Python packages lib dir
        self.pylibdir = os.path.join("lib", "python%s", "site-packages")

        self.sitecfg = None
        self.sitecfgfn = 'site.cfg'
        self.sitecfglibdir = None
        self.sitecfgincdir = None

    def configure_step(self):
        """Set Python packages lib dir."""

        self.log.debug("PythonPackage: configuring")

        python_version = get_software_version('Python')
        if not python_version:
            self.log.error('Python module not loaded.')

        python_short_ver = ".".join(python_version.split(".")[0:2])

        self.pylibdir = self.pylibdir % python_short_ver

        self.log.debug("pylibdir: %s" % self.pylibdir)

        if self.sitecfg is not None:
            # code from python EB_DefaultPythonPackage
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

    def build_step(self):
        """Build Python package using setup.py"""

        cmd = "python setup.py build"
        run_cmd(cmd, log_all=True, simple=True)

    def install_step(self):
        """Install Python package to a custom path using setup.py"""

        abs_pylibdir = os.path.join(self.installdir, self.pylibdir)

        mkdir(abs_pylibdir, parents=True)

        pythonpath = os.getenv('PYTHONPATH')
        env.setvar('PYTHONPATH', ":".join([x for x in [abs_pylibdir, pythonpath] if x is not None]))

        cmd = "python setup.py install --prefix=%s %s" % (self.installdir, self.cfg['installopts'])
        run_cmd(cmd, log_all=True, simple=True)

        if pythonpath is not None:
            env.setvar('PYTHONPATH', pythonpath)

    def sanity_check_step(self, custom_paths=None, custom_commands=None):
        """
        Custom sanity check for Python packages
        """
        if not custom_paths:
            custom_paths = {
                            'files': [],
                            'dirs': ["%s/%s" % (self.pylibdir, self.name.lower())]
                           }

        super(PythonPackage, self).sanity_check_step(custom_paths=custom_paths, custom_commands=custom_commands)

    def make_module_extra(self):
        """Add install path to PYTHONPATH"""

        txt = super(PythonPackage, self).make_module_extra()

        txt += "prepend-path\tPYTHONPATH\t%s\n" % os.path.join(self.installdir , self.pylibdir)

        return txt

class EB_DefaultPythonPackage(Extension):
    """
    Easyblock for Python packages to be included in the Python installation.
    """

    def __init__(self, mself, ext):
        """Custom constructor for EB_DefaultPythonPackage: initialize class variables."""
        super(EB_DefaultPythonPackage, self).__init__(mself, ext)

        self.sitecfg = None
        self.sitecfgfn = 'site.cfg'
        self.sitecfglibdir = None
        self.sitecfgincdir = None
        self.testinstall = False
        self.builddir = mself.builddir
        self.mself = mself
        self.installopts = ''
        self.runtest = None
        self.ext_dir = "%s/%s" % (self.builddir, self.name)
        self.unpack_options = ''

        self.python = get_software_root('Python')

        ver = '.'.join(get_software_version('Python').split('.')[0:2])
        self.python_libdir = os.path.join('lib', 'python%s' % ver, 'site-packages')

        # make sure there's no site.cfg in $HOME, because setup.py will find it and use it
        if os.path.exists(os.path.join(expanduser('~'), 'site.cfg')):
            self.log.error('Found site.cfg in your home directory (%s), please remove it.' % expanduser('~'))

    def configure_step(self):
        """Configure Python package build
        """

        if self.sitecfg: # used by some extensions_step, like numpy, to find certain libs
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

        # sanity checks for python being used
        run_cmd("python -V")
        run_cmd("which python")
        run_cmd("python -c 'import sys; print(sys.executable)'")

    def build_step(self):
        """Build Python package via setup.py"""

        cmd = "python setup.py build "

        run_cmd(cmd, log_all=True, simple=True)

    def install_step(self):
        """Install built Python package"""

        cmd = "python setup.py install --prefix=%s %s" % (self.python, self.installopts)
        run_cmd(cmd, log_all=True, simple=True)

    def test_step(self):
        """Test the compilation
        - default: None
        """
        extrapath = ""
        testinstalldir = os.path.join(self.builddir, "eb_test_install_dir_%s" % self.name)
        if self.testinstall:
            # Install in test directory and export PYTHONPATH
            try:
                os.makedirs(testinstalldir)
            except OSError:
                self.log.exception("Creating testinstalldir %s failed" % testinstalldir)

            cmd = "python setup.py install --prefix=%s %s" % (testinstalldir, self.installopts)
            run_cmd(cmd, log_all=True, simple=True)

            run_cmd("python -c 'import sys; print(sys.path)'")  # print Python search path (debug)
            extrapath = "export PYTHONPATH=%s/%s:$PYTHONPATH && " % (testinstalldir, self.python_libdir)

        if self.runtest:
            cmd = "%s%s" % (extrapath, self.runtest)
            run_cmd(cmd, log_all=True, simple=True)

        if self.testinstall:
            try:
                rmtree2(testinstalldir)
            except OSError, err:
                self.log.exception("Removing testinstalldir %s failed: %s" % (testinstalldir, err))

    def run(self):
        """Perform the actual Python package build/installation procedure"""

        # extract_file
        if not self.src:
            self.log.error("No source found for Python package %s, required for installation. (src: %s)" % \
                           (self.name, self.src))
        self.ext_dir = extract_file("%s" % self.src, "%s/%s" % (self.builddir, self.name), extra_options=self.unpack_options)

        # patch if needed
        if self.patches:
            for patchfile in self.patches:
                if not apply_patch(patchfile, self.ext_dir):
                    self.log.error("Applying patch %s failed" % patchfile)

        # configure, build_step, test, make install
        self.configure_step()
        self.build_step()
        self.test_step()
        self.install_step()

