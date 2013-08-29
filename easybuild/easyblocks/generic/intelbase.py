# #
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
# #
"""
Generic EasyBuild support for installing Intel tools, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os
import shutil
import tempfile

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import rmtree2, run_cmd

# required for deprecated log in static function (ie no self)
from easybuild.framework.easyconfig.licenses import License
from vsc import fancylogger
_log = fancylogger.getLogger('generic.intelbase')


class IntelBase(EasyBlock):
    """
    Base class for Intel software
    - no configure/make : binary release
    - add license_file variable
    """

    def __init__(self, *args, **kwargs):
        """Constructor, adds extra config options"""
        self.license_file = None

        self.home_subdir = os.path.join(os.getenv('HOME'), 'intel')
        self.home_subdir_local = os.path.join(tempfile.gettempdir(), os.getenv('USER'), 'easybuild_intel')

        super(IntelBase, self).__init__(*args, **kwargs)

        # prepare (local) 'intel' home subdir
        self.setup_local_home_subdir()
        self.clean_home_subdir()

    @staticmethod
    def extra_options(extra_vars=None):
        origvars = EasyBlock.extra_options(extra_vars)
        intel_vars = [
                      ('license_activation', ['license_server', "Indicates license activation type (default: 'license_server')", CUSTOM]),
                       # 'usetmppath':
                       # workaround for older SL5 version (5.5 and earlier)
                       # used to be True, but False since SL5.6/SL6
                       # disables TMP_PATH env and command line option
                      ('usetmppath', [False, "Use temporary path for installation (default: False)", CUSTOM]),
                      ('m32', [False, "Enable 32-bit toolchain (default: False)", CUSTOM]),
                     ]

        # Support for old easyconfigs with license parameter
        _log.deprecated('No old style license parameter, use license_file', '2.0')
        intel_vars.append(('license', [None, "License file (default: None)", CUSTOM]))

        intel_vars.extend(origvars)
        return intel_vars

    def clean_home_subdir(self):
        """Remove contents of (local) 'intel' directory home subdir, where stuff is cached."""

        self.log.debug("Cleaning up %s..." % self.home_subdir_local)
        try:
            for tree in os.listdir(self.home_subdir_local):
                self.log.debug("... removing %s subtree" % tree)
                path = os.path.join(self.home_subdir_local, tree)
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
        except OSError, err:
            self.log.error("Cleaning up intel dir %s failed: %s" % (self.home_subdir_local, err))

    def setup_local_home_subdir(self):
        """
        Intel script use $HOME/intel to cache stuff.
        To enable parallel builds, we symlink $HOME/intel to a temporary dir on the local disk."""

        try:
            # make sure local directory exists
            if not os.path.exists(self.home_subdir_local):
                os.makedirs(self.home_subdir_local)

            if os.path.exists(self.home_subdir):
                # if 'intel' dir in $HOME already exists, make sure it's the right symlink
                symlink_ok = os.path.islink(self.home_subdir) and os.path.samefile(self.home_subdir,
                                                                                   self.home_subdir_local)
                if not symlink_ok:
                    # rename current 'intel' dir
                    home_intel_bk = '.'.join([self.home_subdir, "bk_easybuild"])
                    self.log.info("Moving %(ih)s to %(ihl)s, I need %(ih)s myself..." % {'ih': self.home_subdir,
                                                                                         'ihl': home_intel_bk})
                    shutil.move(self.home_subdir, home_intel_bk)

                    # set symlink in place
                    os.symlink(self.home_subdir_local, self.home_subdir)

            else:
                os.symlink(self.home_subdir_local, self.home_subdir)

        except OSError, err:
            self.log.error("Failed to symlink %s to %s: %s" % (self.home_subdir_local, self.home_subdir, err))

    def configure_step(self):
        """Configure: handle license file and clean home dir."""

        lic_env_var = 'INTEL_LICENSE_FILE'
        intel_license_file = os.getenv(lic_env_var)

        if intel_license_file is None:
            self.log.debug("Env var $%s not set, trying 'license_file' easyconfig parameter..." % lic_env_var)
            # obtain license path
            try:
                self.license_file = self.cfg['license_file']
            except:
                # the default should exist
                self.log.deprecated('No new style license_file parameter, license_file is now mandatory', '2.0')
                self.license_file = None

            if self.license_file is None:
                self.log.deprecated('Checking for old style license', '2.0')
                self.cfg.enable_templating = False
                lic = self.cfg['license']
                # old style license is a path (type string)
                if isinstance(lic, License) and isinstance(lic, str):
                    self.log.deprecated('No old style license parameter, license has to be pure License subclass', '2.0')
                    self.license_file = lic
                self.cfg.enable_templating = True

            if self.license_file:
                self.log.info("Using license file %s" % self.license_file)
            else:
                self.log.error("No license file defined")

            # verify license path
            if not os.path.exists(self.license_file):
                self.log.error("Can't find license at %s" % self.license_file)

            # set INTEL_LICENSE_FILE
            env.setvar(lic_env_var, self.license_file)
        else:
            # pick up $INTEL_LICENSE_FILE if it's set
            self.log.info("Picking up Intel license file specification from $%s: %s" % (lic_env_var, intel_license_file))
            self.cfg['license_file'] = intel_license_file
            self.license_file = intel_license_file

        # clean home directory
        self.clean_home_subdir()

    def build_step(self):
        """Binary installation files, so no building."""
        pass

    def install_step(self, silent_cfg_names_map=None):
        """Actual installation

        - create silent cfg file
        - set environment parameters
        - execute command
        """
        if silent_cfg_names_map is None:
            silent_cfg_names_map = {}

        silent = '\n'.join([
            "%(activation_name)s=%(activation)s",
            "%(license_file_name)s=%(license_file)s",
            "%(install_dir_name)s=%(install_dir)s",
            "ACCEPT_EULA=accept",
            "INSTALL_MODE=NONRPM",
            "CONTINUE_WITH_OPTIONAL_ERROR=yes",
        ]) % {
            'activation_name': silent_cfg_names_map.get('activation_name', 'ACTIVATION'),
            'license_file_name': silent_cfg_names_map.get('license_file_name', 'PSET_LICENSE_FILE'),
            'install_dir_name': silent_cfg_names_map.get('install_dir_name', 'PSET_INSTALL_DIR'),
            'activation': self.cfg['license_activation'],
            'license_file': self.license_file,
            'install_dir': silent_cfg_names_map.get('install_dir', self.installdir),
        }

        # we should be already in the correct directory
        silentcfg = os.path.join(os.getcwd(), "silent.cfg")
        try:
            f = open(silentcfg, 'w')
            f.write(silent)
            f.close()
        except:
            self.log.exception("Writing silent cfg % failed" % silent)
        self.log.debug("Contents of %s: %s" % (silentcfg, silent))

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
        env.setvar('LOCAL_INSTALL_VERBOSE', '1')
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
        self.clean_home_subdir()

        super(IntelBase, self).cleanup_step()

    # no default sanity check, needs to be implemented by derived class
