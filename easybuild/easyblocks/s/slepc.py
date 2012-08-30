##
# Copyright 2012 Kenneth Hoste
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
EasyBuild support for SLEPc, implemented as an easyblock
"""

import os
import re

import easybuild.tools.environment as env
from easybuild.framework.application import Application
from easybuild.framework.easyconfig import BUILD, CUSTOM
from easybuild.tools.filetools import run_cmd
from easybuild.tools.modules import get_software_root


class EB_SLEPc(Application):
    """Support for building and installing SLEPc"""

    def __init__(self, *args, **kwargs):
        """Initialize SLEPc custom variables."""
        Application.__init__(self, *args, **kwargs)

        self.slepc_arch_dir = None

        self.slepc_subdir = ''
        if self.getcfg('sourceinstall'):
            self.slepc_subdir = os.path.join('%s-%s' % (self.name().lower(), self.version()),
                                             os.getenv('PETSC_ARCH'))

    @staticmethod
    def extra_options():
        """Add extra config options specific to SLEPc."""
        extra_vars = [
                      ('sourceinstall', [False, "Indicates whether a source installation should be performed (default: False)", CUSTOM]),
                      ('runtest', ['test', "Make target to test build (default: test)", BUILD])
                     ]
        return Application.extra_options(extra_vars)

    def make_builddir(self):
        """Decide whether or not to build in install dir before creating build dir."""
        if self.getcfg('sourceinstall'):
            self.build_in_installdir = True

        Application.make_builddir(self)

    def configure(self):
        """Configure SLEPc by setting configure options and running configure script."""

        # check PETSc dependency
        if not get_software_root("PETSc"):
            self.log.error("PETSc module not loaded?")

        # set SLEPC_DIR environment variable
        env.set('SLEPC_DIR', self.getcfg('startfrom'))
        self.log.debug('SLEPC_DIR: %s' % os.getenv('SLEPC_DIR'))

        # optional dependencies
        depfilter = self.cfg.builddependencies() + ["PETSc"]
        deps = [dep['name'] for dep in self.cfg.dependencies() if not dep['name'] in depfilter]
        for dep in deps:
            deproot = get_software_root(dep)
            if deproot:
                withdep = "--with-%s" % dep.lower()
                self.updatecfg('configopts', '%s=1 %s-dir=%s' % (withdep, withdep, deproot))

        if self.getcfg('sourceinstall'):
            # run configure without --prefix (required)
            cmd = "%s ./configure %s" % (self.getcfg('preconfigopts'), self.getcfg('configopts'))
            (out, _) = run_cmd(cmd, log_all=True, simple=False)
        else:
            # regular './configure --prefix=X' for non-source install
            out = Application.configure(self)

        # check for errors in configure
        error_regexp = re.compile("ERROR")
        if error_regexp.search(out):
            self.log.error("Error(s) detected in configure output!")

        # set default PETSC_ARCH if required
        if not os.getenv('PETSC_ARCH'):
            env.set('PETSC_ARCH' , 'arch-installed-petsc')

    def make_module_req_guess(self):
        """Specify correct LD_LIBRARY_PATH and CPATH for SLEPc installation."""
        guesses = Application.make_module_req_guess(self)

        guesses.update({
                        'CPATH': [os.path.join(self.slepc_subdir, "include")],
                        'LD_LIBRARY_PATH': [os.path.join(self.slepc_subdir, "lib")]
                        })

        return guesses

    def make_module_extra(self):
        """Set SLEPc specific environment variables (SLEPC_DIR)."""
        txt = Application.make_module_extra(self)

        if self.getcfg('sourceinstall'):
            txt += self.moduleGenerator.setEnvironment('SLEPC_DIR', '$root/%s-%s' % (self.name().lower(),
                                                                                     self.version()))

        else:
            txt += self.moduleGenerator.setEnvironment('SLEPC_DIR', '$root')

        return txt

    def sanitycheck(self):
        """Custom sanity check for SLEPc"""
        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths', {
                                             'files': [],
                                             'dirs': [os.path.join(self.slepc_subdir, x) for x in ["conf",
                                                                                                   "include",
                                                                                                   "lib"]]
                                            })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
