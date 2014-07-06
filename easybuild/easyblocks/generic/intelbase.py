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
@author: Ward Poelmans (Ghent University)
"""

import os
import re
import shutil
import tempfile
import glob

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import rmtree2, run_cmd

# required for deprecated log in static function (ie no self)
from easybuild.framework.easyconfig.licenses import License
from vsc import fancylogger
_log = fancylogger.getLogger('generic.intelbase')


# different supported activation types (cfr. Intel documentation)
ACTIVATION_EXIST_LIC = 'exist_lic'  # use a license which exists on the system
ACTIVATION_LIC_FILE = 'license_file'  # use a license file
ACTIVATION_LIC_SERVER = 'license_server'  # use a license server
ACTIVATION_SERIAL = 'serial_number'  # use a serial number
ACTIVATION_TRIAL = 'trial_lic'  # use trial activation
ACTIVATION_TYPES = [
    ACTIVATION_EXIST_LIC,
    ACTIVATION_EXIST_LIC,
    ACTIVATION_LIC_SERVER,
    ACTIVATION_SERIAL,
    ACTIVATION_TRIAL,
]

# silent.cfg parameter name for type of license activation (cfr. options listed above)
ACTIVATION_NAME = 'ACTIVATION_TYPE'  # since icc/ifort v2013_sp1, impi v4.1.1, imkl v11.1
ACTIVATION_NAME_2012 = 'ACTIVATION'  # previous activation type parameter used in older versions
# silent.cfg parameter name for install prefix
INSTALL_DIR_NAME = 'PSET_INSTALL_DIR'
# silent.cfg parameter name for license file/server specification
LICENSE_FILE_NAME = 'ACTIVATION_LICENSE_FILE'  # since icc/ifort v2013_sp1, impi v4.1.1, imkl v11.1
LICENSE_FILE_NAME_2012 = 'PSET_LICENSE_FILE'  # previous license file parameter used in older versions


class IntelBase(EasyBlock):
    """
    Base class for Intel software
    - no configure/make : binary release
    - add license_file variable
    """

    def __init__(self, *args, **kwargs):
        """Constructor, adds extra config options"""
        self.license_file = None
        self.license_env_var = None

        self.home_subdir = os.path.join(os.getenv('HOME'), 'intel')
        common_tmp_dir = os.path.dirname(tempfile.gettempdir())  # common tmp directory, same across nodes
        self.home_subdir_local = os.path.join(common_tmp_dir, os.getenv('USER'), 'easybuild_intel')

        super(IntelBase, self).__init__(*args, **kwargs)

        # prepare (local) 'intel' home subdir
        self.setup_local_home_subdir()
        self.clean_home_subdir()

    @staticmethod
    def extra_options(extra_vars=None):
        extra_vars = dict(EasyBlock.extra_options(extra_vars))
        extra_vars.update({
            'license_activation': [ACTIVATION_LIC_SERVER, "License activation type", CUSTOM],
            # 'usetmppath':
            # workaround for older SL5 version (5.5 and earlier)
            # used to be True, but False since SL5.6/SL6
            # disables TMP_PATH env and command line option
            'usetmppath': [False, "Use temporary path for installation", CUSTOM],
            'm32': [False, "Enable 32-bit toolchain", CUSTOM],
        })

        # Support for old easyconfigs with license parameter
        _log.deprecated('No old style license parameter, use license_file', '2.0')
        extra_vars.update({'license': [None, "License file", CUSTOM]})

        return EasyBlock.extra_options(extra_vars)

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
                self.log.debug("Created local dir %s" % self.home_subdir_local)

            if os.path.exists(self.home_subdir):
                # if 'intel' dir in $HOME already exists, make sure it's the right symlink
                symlink_ok = os.path.islink(self.home_subdir) and os.path.samefile(self.home_subdir,
                                                                                   self.home_subdir_local)
                if not symlink_ok:
                    # rename current 'intel' dir
                    home_intel_bk = tempfile.mkdtemp(dir=os.path.dirname(self.home_subdir),
                                                     prefix='%s.bk.' % os.path.basename(self.home_subdir))
                    self.log.info("Moving %(ih)s to %(ihl)s, I need %(ih)s myself..." % {'ih': self.home_subdir,
                                                                                         'ihl': home_intel_bk})
                    shutil.move(self.home_subdir, home_intel_bk)

                    # set symlink in place
                    os.symlink(self.home_subdir_local, self.home_subdir)
                    self.log.debug("Created symlink (1) %s to %s" % (self.home_subdir, self.home_subdir_local))

            else:
                # if a broken symlink is present, remove it first
                if os.path.islink(self.home_subdir):
                    os.remove(self.home_subdir)
                os.symlink(self.home_subdir_local, self.home_subdir)
                self.log.debug("Created symlink (2) %s to %s" % (self.home_subdir, self.home_subdir_local))

        except OSError, err:
            self.log.error("Failed to symlink %s to %s: %s" % (self.home_subdir_local, self.home_subdir, err))

    def configure_step(self):
        """Configure: handle license file and clean home dir."""

        lic_env_var = None  # environment variable that will be used
        default_lic_env_var = 'INTEL_LICENSE_FILE'
        lic_env_vars = [default_lic_env_var, 'LM_LICENSE_FILE']
        env_var_names = ', '.join(['$%s' % x for x in lic_env_vars])
        lic_env_var_vals = [(var, os.getenv(var)) for var in lic_env_vars]
        license_specs = [(var, e) for (var, val) in lic_env_var_vals if val is not None for e in val.split(os.pathsep)]

        if not license_specs:
            self.log.debug("No env var from %s set, trying 'license_file' easyconfig parameter..." % lic_env_vars)
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
                self.log.error("No license file defined, maybe set one these env vars: %s" % env_var_names)

            # verify license path
            if not os.path.exists(self.license_file):
                tup = (self.license_file, env_var_names)
                self.log.error("%s not found; correct 'license_file', or define one of the these env vars: %s" % tup)

            # set default environment variable for license specification
            env.setvar(default_lic_env_var, self.license_file)
            self.license_env_var = default_lic_env_var
        else:
            valid_license_specs = {}
            # iterate through entries in environment variables until a valid license specification is found
            # valid options are:
            # * an (existing) license file
            # * a directory containing atleast one file named *.lic (only one is used, first listed alphabetically)
            # * a license server, format: <port>@<server>
            server_port_regex = re.compile('^[0-9]+@\S+$')
            for (lic_env_var, license_spec) in license_specs:
                # a value that seems to match a license server specification
                if server_port_regex.match(license_spec):
                    self.log.info("Found license server spec %s in $%s, retaining it" % (license_spec, lic_env_var))
                    valid_license_specs.setdefault(lic_env_var, set()).add(license_spec)

                # an (existing) license file
                elif os.path.isfile(license_spec):
                    self.log.info("Found existing license file %s via $%s, retaining it" % (license_spec, lic_env_var))
                    valid_license_specs.setdefault(lic_env_var, set()).add(license_spec)

                # a directory, should contain at least one *.lic file (use only the first one)
                elif os.path.isdir(license_spec):
                    lic_files = glob.glob("%s/*.lic" % license_spec)
                    if not lic_files:
                        self.log.debug("Found no license files (*.lic) in %s" % license_spec)
                        continue
                    # just pick the first .lic, if it's not correct, $INTEL_LICENSE_FILE should be adjusted instead
                    valid_license_specs.setdefault(lic_env_var, set()).add(lic_files[0])
                    self.log.info('Picked the first *.lic file from $%s: %s' % (lic_env_var, lic_files[0]))

            if not valid_license_specs:
                self.log.error("Cannot find a valid license specification in %s" % license_specs)

            # only retain one environment variable (by order of preference), retain all valid matches for that env var
            for lic_env_var in lic_env_vars:
                if lic_env_var in valid_license_specs:
                    self.license_env_var = lic_env_var
                    retained = valid_license_specs[self.license_env_var]
                    self.license_file = os.pathsep.join(retained)
                    # if we have multiple retained lic specs, specify to 'use a license which exists on the system'
                    if len(retained) > 1:
                        self.cfg['license_activation'] = ACTIVATION_EXIST_LIC
                        # $INTEL_LICENSE_FILE should always be set during installation with existing license
                        env.setvar(default_lic_env_var, self.license_file)
                    break
            if self.license_file is None or self.license_env_var is None:
                self.log.error("self.license_file or self.license_env_var still None, something went horribly wrong...")

            self.cfg['license_file'] = self.license_file
            env.setvar(self.license_env_var, self.license_file)
            self.log.info("Using Intel license specifications from $%s: %s" % (self.license_env_var, self.license_file))

        # clean home directory
        self.clean_home_subdir()

    def build_step(self):
        """Binary installation files, so no building."""
        pass

    def install_step(self, silent_cfg_names_map=None, silent_cfg_extras=None):
        """Actual installation

        - create silent cfg file
        - set environment parameters
        - execute command
        """
        if silent_cfg_names_map is None:
            silent_cfg_names_map = {}

        # license file entry is only applicable with license file or server type of activation
        # also check whether specified activation type makes sense
        lic_activation = self.cfg['license_activation']
        lic_file_server_activations = [ACTIVATION_LIC_FILE, ACTIVATION_LIC_SERVER]
        other_activations = [act for act in ACTIVATION_TYPES if not act in lic_file_server_activations]
        lic_file_entry = ""
        if lic_activation in lic_file_server_activations:
            lic_file_entry = "%(license_file_name)s=%(license_file)s"
        elif not self.cfg['license_activation'] in other_activations:
            self.log.error("Unknown type of activation specified: %s (known :%s)" % (lic_activation, ACTIVATION_TYPES))

        silent = '\n'.join([
            "%(activation_name)s=%(activation)s",
            lic_file_entry,
            "%(install_dir_name)s=%(install_dir)s",
            "ACCEPT_EULA=accept",
            "INSTALL_MODE=NONRPM",
            "CONTINUE_WITH_OPTIONAL_ERROR=yes",
            ""  # Add a newline at the end, so we can easily append if needed
        ]) % {
            'activation_name': silent_cfg_names_map.get('activation_name', ACTIVATION_NAME),
            'license_file_name': silent_cfg_names_map.get('license_file_name', LICENSE_FILE_NAME),
            'install_dir_name': silent_cfg_names_map.get('install_dir_name', INSTALL_DIR_NAME),
            'activation': self.cfg['license_activation'],
            'license_file': self.license_file,
            'install_dir': silent_cfg_names_map.get('install_dir', self.installdir),
        }

        if silent_cfg_extras is not None:
            if isinstance(silent_cfg_extras, dict):
                silent += '\n'.join("%s=%s" % (key, value) for (key, value) in silent_cfg_extras.iteritems())
            else:
                self.log.error("silent_cfg_extras needs to be a dict")

        # we should be already in the correct directory
        silentcfg = os.path.join(os.getcwd(), "silent.cfg")
        try:
            f = open(silentcfg, 'w')
            f.write(silent)
            f.close()
        except:
            self.log.exception("Writing silent cfg % failed" % silent)
        self.log.debug("Contents of %s:\n%s" % (silentcfg, silent))

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
