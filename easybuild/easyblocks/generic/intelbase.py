# #
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
# #
"""
Generic EasyBuild support for installing Intel tools, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Ward Poelmans (Ghent University)
@author: Lumir Jasiok (IT4Innovations)
"""

import os
import re
import shutil
import tempfile
import glob

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import find_flexlm_license, read_file
from easybuild.tools.run import run_cmd

from vsc.utils import fancylogger
_log = fancylogger.getLogger('generic.intelbase')


# different supported activation types (cfr. Intel documentation)
ACTIVATION_EXIST_LIC = 'exist_lic'  # use a license which exists on the system
ACTIVATION_LIC_FILE = 'license_file'  # use a license file
ACTIVATION_LIC_SERVER = 'license_server'  # use a license server
ACTIVATION_SERIAL = 'serial_number'  # use a serial number
ACTIVATION_TRIAL = 'trial_lic'  # use trial activation
ACTIVATION_TYPES = [
    ACTIVATION_EXIST_LIC,
    ACTIVATION_LIC_FILE,
    ACTIVATION_LIC_SERVER,
    ACTIVATION_SERIAL,
    ACTIVATION_TRIAL,
]

# silent.cfg parameter name for type of license activation (cfr. options listed above)
ACTIVATION_NAME = 'ACTIVATION_TYPE'  # since icc/ifort v2013_sp1, impi v4.1.1, imkl v11.1
ACTIVATION_NAME_2012 = 'ACTIVATION'  # previous activation type parameter used in older versions
# silent.cfg parameter name for install prefix
INSTALL_DIR_NAME = 'PSET_INSTALL_DIR'
# silent.cfg parameter name for install mode
INSTALL_MODE_NAME = 'PSET_MODE'
# Older (2015 and previous) silent.cfg parameter name for install mode
INSTALL_MODE_NAME_2015 = 'INSTALL_MODE'
# Install mode for 2016 version
INSTALL_MODE = 'install'
# Install mode for 2015 and older versions
INSTALL_MODE_2015 = 'NONRPM'
# silent.cfg parameter name for license file/server specification
LICENSE_FILE_NAME = 'ACTIVATION_LICENSE_FILE'  # since icc/ifort v2013_sp1, impi v4.1.1, imkl v11.1
LICENSE_FILE_NAME_2012 = 'PSET_LICENSE_FILE'  # previous license file parameter used in older versions

COMP_ALL = 'ALL'
COMP_DEFAULTS = 'DEFAULTS'


class IntelBase(EasyBlock):
    """
    Base class for Intel software
    - no configure/make : binary release
    - add license_file variable
    """

    def __init__(self, *args, **kwargs):
        """Constructor, adds extra config options"""
        super(IntelBase, self).__init__(*args, **kwargs)

        self.license_file = 'UNKNOWN'
        self.license_env_var = 'UNKNOWN'

        self.home_subdir = os.path.join(os.getenv('HOME'), 'intel')
        common_tmp_dir = os.path.dirname(tempfile.gettempdir())  # common tmp directory, same across nodes
        self.home_subdir_local = os.path.join(common_tmp_dir, os.getenv('USER'), 'easybuild_intel')

        self.install_components = None

    @staticmethod
    def extra_options(extra_vars=None):
        extra_vars = EasyBlock.extra_options(extra_vars)
        extra_vars.update({
            'license_activation': [ACTIVATION_LIC_SERVER, "License activation type", CUSTOM],
            # 'usetmppath':
            # workaround for older SL5 version (5.5 and earlier)
            # used to be True, but False since SL5.6/SL6
            # disables TMP_PATH env and command line option
            'usetmppath': [False, "Use temporary path for installation", CUSTOM],
            'm32': [False, "Enable 32-bit toolchain", CUSTOM],
            'components': [None, "List of components to install", CUSTOM],
        })

        return extra_vars

    def parse_components_list(self):
        """parse the regex in the components extra_options and select the matching components
        from the mediaconfig.xml file in the install dir"""

        mediaconfigpath = os.path.join(self.cfg['start_dir'], 'pset', 'mediaconfig.xml')
        if not os.path.isfile(mediaconfigpath):
            raise EasyBuildError("Could not find %s to find list of components." % mediaconfigpath)

        mediaconfig = read_file(mediaconfigpath)
        available_components = re.findall("<Abbr>(?P<component>[^<]+)</Abbr>", mediaconfig, re.M)
        self.log.debug("Intel components found: %s" % available_components)
        self.log.debug("Using regex list: %s" % self.cfg['components'])

        if COMP_ALL in self.cfg['components'] or COMP_DEFAULTS in self.cfg['components']:
            if len(self.cfg['components']) == 1:
                self.install_components = self.cfg['components']
            else:
                raise EasyBuildError("If you specify %s as components, you cannot specify anything else: %s",
                                     ' or '.join([COMP_ALL, COMP_DEFAULTS]), self.cfg['components'])
        else:
            self.install_components = []
            for comp_regex in self.cfg['components']:
                comps = [comp for comp in available_components if re.match(comp_regex, comp)]
                self.install_components.extend(comps)

        self.log.debug("Components to install: %s" % self.install_components)

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
            raise EasyBuildError("Cleaning up intel dir %s failed: %s", self.home_subdir_local, err)

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
            raise EasyBuildError("Failed to symlink %s to %s: %s", self.home_subdir_local, self.home_subdir, err)

    def configure_step(self):
        """Configure: handle license file and clean home dir."""

        # prepare (local) 'intel' home subdir
        self.setup_local_home_subdir()
        self.clean_home_subdir()

        default_lic_env_var = 'INTEL_LICENSE_FILE'
        lic_specs, self.license_env_var = find_flexlm_license(custom_env_vars=[default_lic_env_var],
                                                              lic_specs=[self.cfg['license_file']])

        if lic_specs:
            if self.license_env_var is None:
                self.log.info("Using Intel license specifications from 'license_file': %s", lic_specs)
                self.license_env_var = default_lic_env_var
            else:
                self.log.info("Using Intel license specifications from $%s: %s", self.license_env_var, lic_specs)

            self.license_file = os.pathsep.join(lic_specs)
            env.setvar(self.license_env_var, self.license_file)

            # if we have multiple retained lic specs, specify to 'use a license which exists on the system'
            if len(lic_specs) > 1:
                self.cfg['license_activation'] = ACTIVATION_EXIST_LIC
                # $INTEL_LICENSE_FILE should always be set during installation with existing license
                env.setvar(default_lic_env_var, self.license_file)
        else:
            msg = "No viable license specifications found; "
            msg += "specify 'license_file', or define $INTEL_LICENSE_FILE or $LM_LICENSE_FILE"
            raise EasyBuildError(msg)

        # clean home directory
        self.clean_home_subdir()

        # determine list of components, based on 'components' easyconfig parameter (if specified)
        if self.cfg['components']:
            self.parse_components_list()
        else:
            self.log.debug("No components specified")

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
        lic_file_server_activations = [ACTIVATION_LIC_FILE, ACTIVATION_LIC_SERVER]
        other_activations = [act for act in ACTIVATION_TYPES if act not in lic_file_server_activations]
        lic_file_entry = ""
        if self.cfg['license_activation'] in lic_file_server_activations:
            lic_file_entry = "%(license_file_name)s=%(license_file)s"
        elif not self.cfg['license_activation'] in other_activations:
            raise EasyBuildError("Unknown type of activation specified: %s (known :%s)",
                                 self.cfg['license_activation'], ACTIVATION_TYPES)

        silent = '\n'.join([
            "%(activation_name)s=%(activation)s",
            lic_file_entry,
            "%(install_dir_name)s=%(install_dir)s",
            "ACCEPT_EULA=accept",
            "%(install_mode_name)s=%(install_mode)s",
            "CONTINUE_WITH_OPTIONAL_ERROR=yes",
            ""  # Add a newline at the end, so we can easily append if needed
        ]) % {
            'activation_name': silent_cfg_names_map.get('activation_name', ACTIVATION_NAME),
            'license_file_name': silent_cfg_names_map.get('license_file_name', LICENSE_FILE_NAME),
            'install_dir_name': silent_cfg_names_map.get('install_dir_name', INSTALL_DIR_NAME),
            'activation': self.cfg['license_activation'],
            'license_file': self.license_file,
            'install_dir': silent_cfg_names_map.get('install_dir', self.installdir),
            'install_mode': silent_cfg_names_map.get('install_mode', INSTALL_MODE_2015),
            'install_mode_name': silent_cfg_names_map.get('install_mode_name', INSTALL_MODE_NAME_2015),
        }

        if self.install_components is not None:
            if len(self.install_components) == 1 and self.install_components[0] in [COMP_ALL, COMP_DEFAULTS]:
                # no quotes should be used for ALL or DEFAULTS
                silent += 'COMPONENTS=%s\n' % self.install_components[0]
            elif self.install_components:
                # a list of components is specified (needs quotes)
                silent += 'COMPONENTS="' + ';'.join(self.install_components) + '"\n'
            else:
                raise EasyBuildError("Empty list of matching components obtained via %s", self.cfg['components'])

        if silent_cfg_extras is not None:
            if isinstance(silent_cfg_extras, dict):
                silent += '\n'.join("%s=%s" % (key, value) for (key, value) in silent_cfg_extras.iteritems())
            else:
                raise EasyBuildError("silent_cfg_extras needs to be a dict")

        # we should be already in the correct directory
        silentcfg = os.path.join(os.getcwd(), "silent.cfg")
        try:
            f = open(silentcfg, 'w')
            f.write(silent)
            f.close()
        except:
            raise EasyBuildError("Writing silent cfg, failed", silent)
        self.log.debug("Contents of %s:\n%s" % (silentcfg, silent))

        # workaround for mktmp: create tmp dir and use it
        tmpdir = os.path.join(self.cfg['start_dir'], 'mytmpdir')
        try:
            os.makedirs(tmpdir)
        except:
            raise EasyBuildError("Directory %s can't be created", tmpdir)
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
        return run_cmd(cmd, log_all=True, simple=True, log_output=True)

    def move_after_install(self):
        """Move installed files to correct location after installation."""
        subdir = os.path.join(self.installdir, self.name, self.version)
        self.log.debug("Moving contents of %s to %s" % (subdir, self.installdir))
        try:
            # remove senseless symlinks, e.g. impi_5.0.1 and impi_latest
            majver = '.'.join(self.version.split('.')[:-1])
            for symlink in ['%s_%s' % (self.name, majver), '%s_latest' % self.name]:
                symlink_fp = os.path.join(self.installdir, symlink)
                if os.path.exists(symlink_fp):
                    os.remove(symlink_fp)
            # move contents of 'impi/<version>' dir to installdir
            for fil in os.listdir(subdir):
                source = os.path.join(subdir, fil)
                target = os.path.join(self.installdir, fil)
                self.log.debug("Moving %s to %s" % (source, target))
                shutil.move(source, target)
            shutil.rmtree(os.path.join(self.installdir, self.name))
        except OSError, err:
            raise EasyBuildError("Failed to move contents of %s to %s: %s", subdir, self.installdir, err)

    def make_module_extra(self):
        """Custom variable definitions in module file."""
        txt = super(IntelBase, self).make_module_extra()

        txt += self.module_generator.prepend_paths(self.license_env_var, [self.license_file],
                                                   allow_abs=True, expand_relpaths=False)

        if self.cfg['m32']:
            nlspath = os.path.join('idb', '32', 'locale', '%l_%t', '%N')
        else:
            nlspath = os.path.join('idb', 'intel64', 'locale', '%l_%t', '%N')
        txt += self.module_generator.prepend_paths('NLSPATH', nlspath)

        return txt

    def cleanup_step(self):
        """Cleanup leftover mess

        - clean home dir
        - generic cleanup (get rid of build dir)
        """
        self.clean_home_subdir()

        super(IntelBase, self).cleanup_step()

    # no default sanity check, needs to be implemented by derived class
