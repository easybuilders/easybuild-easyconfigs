##
# Copyright 2015-2016 Bart Oldeman
# Copyright 2016-2016 Forschungszentrum Juelich
#
# This file is triple-licensed under GPLv2 (see below), MIT, and
# BSD three-clause licenses.
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
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
EasyBuild support for installing PGI compilers, implemented as an easyblock

@author: Bart Oldeman (McGill University, Calcul Quebec, Compute Canada)
@author: Damian Alvarez (Forschungszentrum Juelich)
"""
import os
import fileinput
import re
import sys

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd

class EB_PGI(EasyBlock):
    """
    Support for installing the PGI compilers
    """

    @staticmethod
    def extra_options():
        extra_vars = {
            'install_amd': [True, "Install AMD software components", CUSTOM],
            'install_java': [True, "Install Java JRE for graphical debugger",  CUSTOM],
            'install_managed': [True, "Install OpenACC Unified Memory Evaluation package", CUSTOM],
            'install_nvidia': [True, "Install CUDA Toolkit Components", CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Easyblock constructor, define custom class variables specific to PGI."""
        super(EB_PGI, self).__init__(*args, **kwargs)

        self.license_file = 'UNKNOWN'
        self.license_env_var = 'UNKNOWN' # Probably not really necessary for PGI

        self.install_subdir = os.path.join('linux86-64', self.version)

    def configure_step(self):
        """
        Handle license file. It mimics intelbase.py behaviour. It should be merged into the framekwork
        at some point
        """
        lic_env_var = None  # environment variable that will be used
        default_lic_env_var = 'LM_LICENSE_FILE'
        lic_env_vars = [default_lic_env_var]
        env_var_names = ', '.join(['$%s' % x for x in lic_env_vars])
        lic_env_var_vals = [(var, os.getenv(var)) for var in lic_env_vars]
        license_specs = [(var, e) for (var, val) in lic_env_var_vals if val is not None for e in val.split(os.pathsep)]

        if not license_specs:
            self.log.debug("No env var from %s set, trying 'license_file' easyconfig parameter..." % lic_env_vars)
            # obtain license path
            self.license_file = self.cfg['license_file']

            if self.license_file:
                self.log.info("Using license file %s" % self.license_file)
            else:
                raise EasyBuildError("No license file defined, maybe set one these env vars: %s", env_var_names)

            # verify license path
            if not os.path.exists(self.license_file):
                raise EasyBuildError("%s not found; correct 'license_file', or define one of the these env vars: %s",
                                     self.license_file, env_var_names)

            # set default environment variable for license specification
            env.setvar(default_lic_env_var, self.license_file)
            self.license_env_var = default_lic_env_var
        else:
            valid_license_specs = {}
            # iterate through entries in environment variables until a valid license specification is found
            # valid options are:
            # * an (existing) license file
            # * a directory containing atleast one file named *.dat (only one is used, first listed alphabetically)
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

                # a directory, should contain at least one *.dat file (use only the first one)
                elif os.path.isdir(license_spec):
                    lic_files = glob.glob("%s/*.dat" % license_spec)
                    if not lic_files:
                        self.log.debug("Found no license files (*.dat) in %s" % license_spec)
                        continue
                    # just pick the first .dat, if it's not correct, $LM_LICENSE_FILE should be adjusted instead
                    valid_license_specs.setdefault(lic_env_var, set()).add(lic_files[0])
                    self.log.info('Picked the first *.lic file from $%s: %s' % (lic_env_var, lic_files[0]))

            if not valid_license_specs:
                raise EasyBuildError("Cannot find a valid license specification in %s", license_specs)

            # only retain one environment variable (by order of preference), retain all valid matches for that env var
            for lic_env_var in lic_env_vars:
                if lic_env_var in valid_license_specs:
                    self.license_env_var = lic_env_var
                    retained = valid_license_specs[self.license_env_var]
                    self.license_file = os.pathsep.join(retained)
                    break
            if self.license_file is None or self.license_env_var is None:
                raise EasyBuildError("self.license_file or self.license_env_var still None, "
                                     "something went horribly wrong...")

            self.cfg['license_file'] = self.license_file
            env.setvar(self.license_env_var, self.license_file)
            self.log.info("Using PGI license specifications from $%s: %s", self.license_env_var, self.license_file)

    def build_step(self):
        """
        Dummy build method: nothing to build
        """
        pass

    def install_step(self):
        """Install by running install command."""

        pgi_env_vars = {
            'PGI_ACCEPT_EULA': 'accept',
            'PGI_INSTALL_AMD': str(self.cfg['install_amd']).lower(),
            'PGI_INSTALL_DIR': self.installdir,
            'PGI_INSTALL_JAVA': str(self.cfg['install_java']).lower(),
            'PGI_INSTALL_MANAGED': str(self.cfg['install_managed']).lower(),
            'PGI_INSTALL_NVIDIA': str(self.cfg['install_nvidia']).lower(),
            'PGI_SILENT': 'true',
            }
        cmd = "%s ./install" % ' '.join(['%s=%s' % x for x in sorted(pgi_env_vars.items())])
        run_cmd(cmd, log_all=True, simple=True)

        # make sure localrc uses GCC in PATH, not always the system GCC, and does not use a system g77 but gfortran
        install_abs_subdir = os.path.join(self.installdir, self.install_subdir)
        filename = os.path.join(install_abs_subdir, "bin", "makelocalrc")
        for line in fileinput.input(filename, inplace='1', backup='.orig'):
            line = re.sub(r"^PATH=/", r"#PATH=/", line)
            sys.stdout.write(line)

        cmd = "%s -x %s -g77 /" % (filename, install_abs_subdir)
        run_cmd(cmd, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for PGI"""
        prefix = self.install_subdir
        custom_paths = {
                        'files': [os.path.join(prefix, "bin", "pgcc")],
                        'dirs': [os.path.join(prefix, "bin"), os.path.join(prefix, "lib"),
                                 os.path.join(prefix, "include"), os.path.join(prefix, "man")]
                       }
        super(EB_PGI, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Prefix subdirectories in PGI install directory considered for environment variables defined in module file."""
        dirs = super(EB_PGI, self).make_module_req_guess()
        for key in dirs:
            dirs[key] = [os.path.join(self.install_subdir, d) for d in dirs[key]]

        # $CPATH should not be defined in module for PGI, it causes problems
        # cfr. https://github.com/hpcugent/easybuild-easyblocks/issues/830
        if 'CPATH' in dirs:
            self.log.info("Removing $CPATH entry: %s", dirs['CPATH']
            del dirs['CPATH']

        return dirs

    def make_module_extra(self):
        """Add environment variables LM_LICENSE_FILE and PGI for license file and PGI location"""
        txt = super(EB_PGI, self).make_module_extra()
        txt += self.module_generator.prepend_paths(self.license_env_var, [self.license_file], allow_abs=True, expand_relpaths=False)
        txt += self.module_generator.set_environment('PGI', self.installdir)
        return txt
