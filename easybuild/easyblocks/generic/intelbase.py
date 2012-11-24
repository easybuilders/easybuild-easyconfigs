##
# Copyright 2009-2012 Ghent University
# Copyright 2009-2012 Stijn De Weirdt
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
##
"""
Generic EasyBuild support for installing Intel tools, implemented as an easyblock
"""

import fileinput
import os
import random
import re
import string
import sys

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
from easybuild.tools.filetools import rmtree2, run_cmd


class IntelBase(EasyBlock):
    """
    Base class for Intel software
    - no configure/make : binary release
    - add license variable
    """

    def __init__(self, *args, **kwargs):
        """Constructor, adds extra config options"""
        self.license = None
        # generate a randomly suffixed name for the 'intel' home subdirectory
        random_suffix = ''.join(random.choice(string.ascii_letters) for _ in xrange(5))
        self.home_subdir = 'intel_%s' % random_suffix
        super(IntelBase, self).__init__(*args, **kwargs)

    @staticmethod
    def extra_options(extra_vars=None):
        origvars = EasyBlock.extra_options(extra_vars)
        intel_vars = [
                      ('license', [None, "License file path (default: None)", MANDATORY]),
                      ('license_activation', ['license_server', "Indicates license activation type (default: 'license_server')", CUSTOM]),
                       # 'usetmppath':
                       # workaround for older SL5 version (5.5 and earlier)
                       # used to be True, but False since SL5.6/SL6
                       # disables TMP_PATH env and command line option
                      ('usetmppath', [False, "Use temporary path for installation (default: False)", CUSTOM]),
                      ('m32', [False, "Enable 32-bit toolchain (default: False)", CUSTOM]),
                     ]
        intel_vars.extend(origvars)
        return intel_vars

    def clean_homedir(self):
        """Remove 'intel' directory from home directory, where stuff is cached."""
        intelhome = os.path.join(os.getenv('HOME'), self.home_subdir)
        if os.path.exists(intelhome):
            try:
                rmtree2(intelhome)
                self.log.info("Cleaning up intel dir %s" % intelhome)
            except OSError, err:
                self.log.warning("Cleaning up intel dir %s failed: %s" % (intelhome, err))

    def configure_step(self):
        """Configure: handle license file and clean home dir."""

        # obtain license path
        self.license = self.cfg['license']
        if self.license:
            self.log.info("Using license %s" % self.license)
        else:
            self.log.error("No license defined")

        # verify license path
        if not os.path.exists(self.license):
            self.log.error("Can't find license at %s" % self.license)

        # set INTEL_LICENSE_FILE
        env.setvar("INTEL_LICENSE_FILE", self.license)

        # patch install scripts with randomly suffixed intel hom subdir
        for fn in ["install.sh", "pset/install.sh", "pset/iat/iat_install.sh", 
                   "data/install_mpi.sh", "pset/install_cc.sh", "pset/install_fc.sh"]:
            try:
                if os.path.isfile(fn):
                    self.log.info("Patching %s with intel home subdir %s" % (fn, self.home_subdir))
                    for line in fileinput.input(fn, inplace=1, backup='.orig'):
                        line = re.sub(r'(.*)(NONRPM_DB_PREFIX="\$HOME/)intel(.*)', 
                                      r'\1\2%s\3' % self.home_subdir, line)
                        line = re.sub(r'(.*)(DEFAULT_DB_PREFIX="\$\(echo ~\)/)intel(.*)',
                                      r'\1\2%s\3' % self.home_subdir, line)
                        sys.stdout.write(line)
            except (OSError, IOError), err:
                self.log.error("Failed to modify install script %s with randomly suffixed home subdir: %s" % (fn, err))

        # clean home directory
        self.clean_homedir()

    def build_step(self):
        """Binary installation files, so no building."""
        pass

    def install_step(self):
        """Actual installation

        - create silent cfg file
        - set environment parameters
        - execute command
        """
        silent = """
ACTIVATION=%s
PSET_LICENSE_FILE=%s
PSET_INSTALL_DIR=%s
ACCEPT_EULA=accept
INSTALL_MODE=NONRPM
CONTINUE_WITH_OPTIONAL_ERROR=yes
""" % (self.cfg['license_activation'], self.license, self.installdir)

        # we should be already in the correct directory
        silentcfg = os.path.join(os.getcwd(), "silent.cfg")
        try:
            f = open(silentcfg, 'w')
            f.write(silent)
            f.close()
        except:
            self.log.exception("Writing silent cfg % failed" % silent)

        # workaround for mktmp: create tmp dir and use it
        tmpdir = os.path.join(self.cfg['start_dir'], 'mytmpdir')
        try:
            os.makedirs(tmpdir)
        except:
            self.log.exception("Directory %s can't be created" % (tmpdir))
        tmppathopt = ''
        if self.cfg['usetmppath']:
            env.setvar('TMP_PATH', tmpdir)
            tmppathopt = "-t %s" % tmpdir

        # set some extra env variables
        env.setvar('LOCAL_INSTALL_VERBOSE','1')
        env.setvar('VERBOSE_MODE', '1')

        env.setvar('INSTALL_PATH', self.installdir)

        # perform installation
        cmd = "./install.sh %s -s %s" % (tmppathopt, silentcfg)
        return run_cmd(cmd, log_all=True, simple=True)

    def cleanup_step(self):
        """Cleanup leftover mess

        - clean home dir
        - generic cleanup (get rid of build dir)
        """
        self.clean_homedir()

        super(IntelBase, self).cleanup_step()

    # no default sanity check, needs to be implemented by derived class
