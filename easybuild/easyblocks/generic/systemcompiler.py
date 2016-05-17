##
# Copyright 2015-2016 Ghent University
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
EasyBuild support for using (already installed/existing) system compiler instead of a full install via EasyBuild.

@author Bernd Mohr (Juelich Supercomputing Centre)
@author Kenneth Hoste (Ghent University)
"""
import os
import re

from easybuild.easyblocks.generic.bundle import Bundle
from easybuild.tools.filetools import read_file, which
from easybuild.tools.run import run_cmd
from easybuild.framework.easyconfig.easyconfig import ActiveMNS
from easybuild.tools.build_log import EasyBuildError


class SystemCompiler(Bundle):
    """
    Support for generating a module file for the system compiler with specified name.

    The compiler is expected to be available in $PATH, required libraries are assumed to be readily available.

    Specifying 'system' as a version leads to using the derived compiler version in the generated module;
    if an actual version is specified, it is checked against the derived version of the system compiler that was found.
    """

    def extract_compiler_version(self, txt):
        """Extract compiler version from provided string."""
        # look for 3-4 digit version number, surrounded by spaces
        # examples:
        # gcc (GCC) 4.4.7 20120313 (Red Hat 4.4.7-11)
        # Intel(R) C Intel(R) 64 Compiler XE for applications running on Intel(R) 64, Version 15.0.1.133 Build 20141023
        version_regex = re.compile(r'\s([0-9]+(?:\.[0-9]+){1,3})\s', re.M)
        res = version_regex.search(txt)
        if res:
            self.compiler_version = res.group(1)
            self.log.debug("Extracted compiler version '%s' from: %s", self.compiler_version, txt)
        else:
            raise EasyBuildError("Failed to extract compiler version using regex pattern '%s' from: %s",
                                 version_regex.pattern, txt)

    def __init__(self, *args, **kwargs):
        """Extra initialization: determine system compiler version and prefix."""
        super(SystemCompiler, self).__init__(*args, **kwargs)

        # Determine compiler path (real path, with resolved symlinks)
        compiler_name = self.cfg['name'].lower()
        path_to_compiler = which(compiler_name)
        if path_to_compiler:
            path_to_compiler = os.path.realpath(path_to_compiler)
            self.log.info("Found path to compiler '%s' (with symlinks resolved): %s", compiler_name, path_to_compiler)
        else:
            raise EasyBuildError("%s not found in $PATH", compiler_name)

        # Determine compiler version and installation prefix
        if compiler_name == 'gcc':
            out, _ = run_cmd("gcc --version", simple=False)
            self.extract_compiler_version(out)

            # strip off 'bin/gcc'
            self.compiler_prefix = os.path.dirname(os.path.dirname(path_to_compiler))

        elif compiler_name in ['icc', 'ifort']:
            out, _ = run_cmd("%s -V" % compiler_name, simple=False)
            self.extract_compiler_version(out)

            intelvars_fn = path_to_compiler + 'vars.sh'
            if os.path.isfile(intelvars_fn):
                self.log.debug("Trying to determine compiler install prefix from %s", intelvars_fn)
                intelvars_txt = read_file(intelvars_fn)
                prod_dir_regex = re.compile(r'^PROD_DIR=(.*)$', re.M)
                res = prod_dir_regex.search(intelvars_txt)
                if res:
                    self.compiler_prefix = res.group(1)
                else:
                    raise EasyBuildError("Failed to determine %s installation prefix from %s",
                                          compiler_name, intelvars_fn)
            else:
                # strip off 'bin/intel*/icc'
                self.compiler_prefix = os.path.dirname(os.path.dirname(os.path.dirname(path_to_compiler)))

        else:
            raise EasyBuildError("Unknown system compiler %s" % self.cfg['name'])

        self.log.debug("Derived version/install prefix for system compiler %s: %s, %s",
                       compiler_name, self.compiler_version, self.compiler_prefix)

        # If EasyConfig specified "real" version (not 'system' which means 'derive automatically'), check it
        if self.cfg['version'] == 'system':
            self.log.info("Found specified version '%s', going with derived compiler version '%s'",
                          self.cfg['version'], self.compiler_version)
        elif self.cfg['version'] != self.compiler_version:
            raise EasyBuildError("Specified version (%s) does not match version reported by compiler (%s)" %
                                 (self.cfg['version'], self.compiler_version))

        # fix installdir and module names (may differ because of changes to version)
        mns = ActiveMNS()
        self.cfg.full_mod_name = mns.det_full_module_name(self.cfg)
        self.cfg.short_mod_name = mns.det_short_module_name(self.cfg)
        self.cfg.mod_subdir = mns.det_module_subdir(self.cfg)

        # keep track of original values, for restoring later
        self.orig_version = self.cfg['version']
        self.orig_installdir = self.installdir

    def make_installdir(self, dontcreate=None):
        """Custom implementation of make installdir: do nothing, do not touch system compiler directories and files."""
        pass

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for.  Return empty dict for a system compiler.
        """
        return {}

    def make_module_step(self, fake=False):
        """
        Custom module step for SystemCompiler: make 'EBROOT' and 'EBVERSION' reflect actual system compiler version
        and install path.
        """
        # For module file generation: temporarly set version and installdir to system compiler values
        self.cfg['version'] = self.compiler_version
        self.installdir = self.compiler_prefix

        # Generate module
        res = super(SystemCompiler, self).make_module_step(fake=fake)

        # Reset version and installdir to EasyBuild values
        self.installdir = self.orig_installdir
        self.cfg['version'] = self.orig_version
        return res

    def make_module_extend_modpath(self):
        """
        Custom prepend-path statements for extending $MODULEPATH: use version specified in easyconfig file (e.g.,
        "system") rather than the actual version (e.g., "4.8.2").
        """
        # temporarly set switch back to version specified in easyconfig file (e.g., "system")
        self.cfg['version'] = self.orig_version

        # Retrieve module path extensions
        res = super(SystemCompiler, self).make_module_extend_modpath()

        # Reset to actual compiler version (e.g., "4.8.2")
        self.cfg['version'] = self.compiler_version
        return res
