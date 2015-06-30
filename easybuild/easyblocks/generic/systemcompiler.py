##
# Copyright 2009-2015 Ghent University
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
EasyBuild support for using (already installed/existing) system compiler instead of a full install via EasyBuild.

@author Bernd Mohr (Juelich Supercomputing Centre)
@author Kenneth Hoste (Ghent University)
"""
import os
import re

from easybuild.easyblocks.generic.bundle import Bundle
from easybuild.tools.filetools import which
from easybuild.tools.run import run_cmd
from easybuild.framework.easyconfig.easyconfig import ActiveMNS
from easybuild.tools.build_log import EasyBuildError


class SystemCompiler(Bundle):
    """Create EasyBuild 'dummy' module for system compiler."""

    #
    # INIT
    #
    def __init__(self, *args, **kwargs):
        """Extra initialization: determine system compiler version and prefix."""
        super(SystemCompiler, self).__init__(*args, **kwargs)

        # Determine compiler path
        self.compiler_name = self.cfg['name'].lower()
        path_to_compiler = which(self.compiler_name)
        if path_to_compiler is None:
            raise EasyBuildError("%s not in $PATH" % self.compiler_name)

        # Determine compiler version and prefix
        if self.compiler_name == 'gcc':
            out, _ = run_cmd('gcc --version', simple=False)
            self.compiler_version = re.findall("([0-9]+(?:\.[0-9]+){1,3})", out)[0]
            # strip off "gcc" and "bin"
            self.compiler_prefix = os.path.dirname(os.path.dirname(path_to_compiler))
            self.cfg['homepage'] = "http://gcc.gnu.org/"

        elif self.compiler_name == 'icc' or self.compiler_name == 'ifort':
            out, _ = run_cmd('icc -V', simple=False)
            self.compiler_version = re.findall("([0-9]+(?:\.[0-9]+){1,3})", out)[0]

            intelvars_fn = path_to_compiler + "vars.sh"
            prefix = None
            if os.path.isfile(intelvars_fn):
                for line in open(intelvars_fn, 'r'):
                     prefix = re.findall("^PROD_DIR=(.*)$", line)
                     if prefix:
                        break
                if prefix:
                    self.compiler_prefix = prefix[0]
                else:
                    raise EasyBuildError("Cannot determine %s prefix" % self.compiler_name)
            else:
                # strip off "icc", "intel*" and "bin"
                self.compiler_prefix = os.path.dirname(os.path.dirname(os.path.dirname(path_to_icc)))
            self.cfg['homepage'] = "http://software.intel.com/en-us/intel-compilers/"

        else:
            raise EasyBuildError("Unknown system compiler %s" % self.cfg['name'])

        # If EasyConfig specified "real" version (not 'system' which means 'derive automatically'), check it
        if self.cfg['version'] != 'system' and self.cfg['version'] != self.compiler_version:
            raise EasyBuildError("Specified version (%s) does not match version reported by compiler (%s)" %
                                 (self.cfg['version'], self.compiler_version))

        # Provide suitable default values for system compiler module file
        default_desc = "EasyBuild wrapper for system compiler %s-%s" % (self.compiler_name, self.compiler_version)
        if not self.cfg['description']:
            self.cfg['description'] = default_desc

        # Ensure moduleclass is set correctly
        self.cfg['moduleclass'] = 'compiler'

        # set and remember EasyBuild installdir (modeled after: easybuild/framework/easyconfig/easyconfig.py)
        mns = ActiveMNS()
        self.cfg.full_mod_name = mns.det_full_module_name(self.cfg)
        self.cfg.short_mod_name = mns.det_short_module_name(self.cfg)
        self.cfg.mod_subdir = mns.det_module_subdir(self.cfg)
        self.orig_installdir = self.installdir

    #
    # DIRECTORY UTILITY FUNCTIONS
    #
    def make_installdir(self, dontcreate=None):
        """Custom version: Do not to touch system compiler directories and files."""
        pass

    #
    # MODULE UTILITY FUNCTIONS
    #
    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for.  Return empty dict for a system compiler.
        """
        return {}

    #
    # STEP FUNCTIONS
    #
    def post_install_step(self):
        """Custom version: Do not to touch system compiler directories and files."""
        pass

    def make_module_step(self, fake=False):
        """Custom module step for SystemCompiler: make 'EBROOT' and 'EBVERSION' reflect system compiler values."""
        self.orig_version = self.cfg['version']

        # For module file generation: temporarly set version and installdir to system compiler values
        self.cfg['version'] = self.compiler_version
        self.installdir= self.compiler_prefix

        # Generate module
        res = super(SystemCompiler, self).make_module_step(fake=fake)

        # Reset version and installdir to EasyBuild values
        self.installdir = self.orig_installdir
        self.cfg['version'] = self.orig_version
        return res
