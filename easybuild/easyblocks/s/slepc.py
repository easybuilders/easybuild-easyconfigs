##
# Copyright 2009-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
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
EasyBuild support for SLEPc, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""

import os
import re
from distutils.version import LooseVersion

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import BUILD, CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd


class EB_SLEPc(ConfigureMake):
    """Support for building and installing SLEPc"""

    @staticmethod
    def extra_options():
        """Add extra config options specific to SLEPc."""
        extra_vars = {
            'runtest': ['test', "Make target to test build", BUILD],
            'petsc_arch': [None, "PETSc architecture to use (value for $PETSC_ARCH)", CUSTOM],
            'sourceinstall': [False, "Indicates whether a source installation should be performed", CUSTOM],
        }
        return ConfigureMake.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Initialize SLEPc custom variables."""
        super(EB_SLEPc, self).__init__(*args, **kwargs)

        self.slepc_subdir = ''

    def make_builddir(self):
        """Decide whether or not to build in install dir before creating build dir."""
        if self.cfg['sourceinstall']:
            self.build_in_installdir = True

        super(EB_SLEPc, self).make_builddir()

    def configure_step(self):
        """Configure SLEPc by setting configure options and running configure script."""

        # check PETSc dependency
        if not get_software_root("PETSc"):
            raise EasyBuildError("PETSc module not loaded?")

        # set SLEPC_DIR environment variable
        env.setvar('SLEPC_DIR', self.cfg['start_dir'])
        self.log.debug('SLEPC_DIR: %s' % os.getenv('SLEPC_DIR'))

        # optional dependencies
        depfilter = self.cfg.builddependencies() + ["PETSc"]
        deps = [dep['name'] for dep in self.cfg.dependencies() if not dep['name'] in depfilter]
        for dep in deps:
            deproot = get_software_root(dep)
            if deproot:
                withdep = "--with-%s" % dep.lower()
                self.cfg.update('configopts', '%s=1 %s-dir=%s' % (withdep, withdep, deproot))

        if self.cfg['sourceinstall']:
            # run configure without --prefix (required)
            cmd = "%s ./configure %s" % (self.cfg['preconfigopts'], self.cfg['configopts'])
            (out, _) = run_cmd(cmd, log_all=True, simple=False)
        else:
            # regular './configure --prefix=X' for non-source install
            
            # make sure old install dir is removed first
            self.make_installdir(dontcreate=True)

            out = super(EB_SLEPc, self).configure_step()

        # check for errors in configure
        error_regexp = re.compile("ERROR")
        if error_regexp.search(out):
            raise EasyBuildError("Error(s) detected in configure output!")

        # define $PETSC_ARCH
        petsc_arch = self.cfg['petsc_arch']
        if self.cfg['petsc_arch'] is None:
            petsc_arch = 'arch-installed-petsc'

        env.setvar('PETSC_ARCH', petsc_arch)

        if self.cfg['sourceinstall']:
            self.slepc_subdir = os.path.join('%s-%s' % (self.name.lower(), self.version), petsc_arch)

        # SLEPc > 3.5, make does not accept -j
        if LooseVersion(self.version) >= LooseVersion("3.5"):
            self.cfg['parallel'] = None

    def make_module_req_guess(self):
        """Specify correct LD_LIBRARY_PATH and CPATH for SLEPc installation."""
        guesses = super(EB_SLEPc, self).make_module_req_guess()

        guesses.update({
            'CPATH': [os.path.join(self.slepc_subdir, "include")],
            'LD_LIBRARY_PATH': [os.path.join(self.slepc_subdir, "lib")],
        })

        return guesses

    def make_module_extra(self):
        """Set SLEPc specific environment variables (SLEPC_DIR)."""
        txt = super(EB_SLEPc, self).make_module_extra()

        if self.cfg['sourceinstall']:
            subdir = '%s-%s' % (self.name.lower(), self.version)
            txt += self.module_generator.set_environment('SLEPC_DIR', os.path.join(self.installdir, subdir))

        else:
            txt += self.module_generator.set_environment('SLEPC_DIR', self.installdir)

        return txt

    def sanity_check_step(self):
        """Custom sanity check for SLEPc"""
        custom_paths = {
            'files': [],
            'dirs': [os.path.join(self.slepc_subdir, x) for x in ['include', 'lib']],
        }
        if LooseVersion(self.version) < LooseVersion('3.6'):
            custom_paths['dirs'].append('conf')
        else:
            custom_paths['dirs'].append(os.path.join('lib', 'slepc', 'conf'))
        super(EB_SLEPc, self).sanity_check_step(custom_paths=custom_paths)
