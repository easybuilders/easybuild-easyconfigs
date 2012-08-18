##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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
Generic EasyBuild support for installing Intel tools, implemented as an easyblock
"""

import os
import shutil

import easybuild.tools.environment as env
from easybuild.framework.application import Application
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
from easybuild.tools.filetools import run_cmd


class IntelBase(Application):
    """
    Base class for Intel software
    - no configure/make : binary release
    - add license variable
    """

    def __init__(self, *args, **kwargs):
        """Constructor, adds extra config options"""
        self.license = None
        Application.__init__(self, *args, **kwargs)

    @staticmethod
    def extra_options(extra_vars=None):
        vars = Application.extra_options(extra_vars)
        intel_vars = [
                      ('license', [None, "License file path (default: None)", MANDATORY]),
                      ('license_activation', ['license_server', "Indicates license activation type (default: 'license_server')", CUSTOM]),
                       # 'usetmppath':
                       # workaround for older SL5 version (5.5 and earlier)
                       # used to be True, but False since SL5.6/SL6
                       # disables TMP_PATH env and command line option
                      ('usetmppath', [False, "Use temporary path for installation (default: False)", CUSTOM]),
                      ('m32', [False, "Enable 32-bit toolkit (default: False)", CUSTOM]),
                     ]
        intel_vars.extend(vars)
        return intel_vars


    def clean_homedir(self):
        """Remove 'intel' directory from home directory, where stuff is cached."""
        intelhome = os.path.join(os.getenv('HOME'), 'intel')
        if os.path.exists(intelhome):
            try:
                shutil.rmtree(intelhome)
                self.log.info("Cleaning up intel dir %s" % intelhome)
            except OSError, err:
                self.log.warning("Cleaning up intel dir %s failed: %s" % (intelhome, err))

    def configure(self):
        """Configure: handle license file and clean home dir."""

        # obtain license path
        self.license = self.getcfg('license')
        if self.license:
            self.log.info("Using license %s" % self.license)
        else:
            self.log.error("No license defined")

        # verify license path
        if not os.path.exists(self.license):
            self.log.error("Can't find license at %s" % self.license)

        # set INTEL_LICENSE_FILE
        env.set("INTEL_LICENSE_FILE", self.license)

        # clean home directory
        self.clean_homedir()

    def make(self):
        """Binary installation files, so no building."""
        pass

    def make_install(self):
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
""" % (self.getcfg('license_activation'), self.license, self.installdir)

        # we should be already in the correct directory
        silentcfg = os.path.join(os.getcwd(), "silent.cfg")
        try:
            f = open(silentcfg, 'w')
            f.write(silent)
            f.close()
        except:
            self.log.exception("Writing silent cfg % failed" % silent)

        # workaround for mktmp: create tmp dir and use it
        tmpdir = os.path.join(self.getcfg('startfrom'), 'mytmpdir')
        try:
            os.makedirs(tmpdir)
        except:
            self.log.exception("Directory %s can't be created" % (tmpdir))
        tmppathopt = ''
        if self.getcfg('usetmppath'):
            env.set('TMP_PATH', tmpdir)
            tmppathopt = "-t %s" % tmpdir

        # set some extra env variables
        env.set('LOCAL_INSTALL_VERBOSE','1')
        env.set('VERBOSE_MODE', '1')

        env.set('INSTALL_PATH', self.installdir)

        # perform installation
        cmd = "./install.sh %s -s %s" % (tmppathopt, silentcfg)
        return run_cmd(cmd, log_all=True, simple=True)

    def cleanup(self):
        """Cleanup leftover mess

        - clean home dir
        - generic cleanup (get rid of build dir)
        """
        self.clean_homedir()

        Application.cleanup(self)

    # no default sanity check, needs to be implemented by derived class
