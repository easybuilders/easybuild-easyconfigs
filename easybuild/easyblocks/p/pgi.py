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
from easybuild.tools.filetools import find_flexlm_license, write_file
from easybuild.tools.run import run_cmd
from easybuild.tools.modules import get_software_root


# contents for siterc file to make PGI pick up $LIBRARY_PATH
# cfr. https://www.pgroup.com/support/link.htm#lib_path_ldflags
SITERC_LIBRARY_PATH = """
# get the value of the environment variable LIBRARY_PATH
variable LIBRARY_PATH is environment(LIBRARY_PATH);

# split this value at colons, separate by -L, prepend 1st one by -L
variable library_path is
default($if($LIBRARY_PATH,-L$replace($LIBRARY_PATH,":", -L)));

# add the -L arguments to the link line
append LDLIBARGS=$library_path;

# also include the location where libm & co live on Debian-based systems
# cfr. https://github.com/hpcugent/easybuild-easyblocks/pull/919
append LDLIBARGS=-L/usr/lib/x86_64-linux-gnu;
"""


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
        Handle license file. 
        """
        default_lic_env_var = 'PGROUPD_LICENSE_FILE'
        lic_specs, self.license_env_var = find_flexlm_license(custom_env_vars=[default_lic_env_var],
                                                              lic_specs=[self.cfg['license_file']])

        if lic_specs:
            if self.license_env_var is None:
                self.log.info("Using PGI license specifications from 'license_file': %s", lic_specs)
                self.license_env_var = default_lic_env_var
            else:
                self.log.info("Using PGI license specifications from %s: %s", self.license_env_var, lic_specs)

            self.license_file = os.pathsep.join(lic_specs)
            env.setvar(self.license_env_var, self.license_file)

        else:
            raise EasyBuildError("No viable license specifications found; specify 'license_file' or " +
                                 "define $PGROUPD_LICENSE_FILE or $LM_LICENSE_FILE")


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
        
        # If an OS libnuma is NOT found, makelocalrc creates symbolic links to libpgnuma.so
        # If we use the EB libnuma, delete those symbolic links to ensure they are not used
        if get_software_root("numactl"):
            for filename in ["libnuma.so", "libnuma.so.1"]:
                path = os.path.join(install_abs_subdir, "lib", filename)
                if os.path.islink(path):
                    os.remove(path)

        # install (or update) siterc file to make PGI consider $LIBRARY_PATH
        siterc_path = os.path.join(self.installdir, self.install_subdir, 'bin', 'siterc')
        write_file(siterc_path, SITERC_LIBRARY_PATH, append=True)
        self.log.info("Appended instructions to pick up $LIBRARY_PATH to siterc file at %s: %s",
                      siterc_path, SITERC_LIBRARY_PATH)

    def sanity_check_step(self):
        """Custom sanity check for PGI"""
        prefix = self.install_subdir
        custom_paths = {
            'files': [os.path.join(prefix, 'bin', x) for x in ['pgcc', 'pgc++', 'pgf77', 'pgfortran', 'siterc']],
            'dirs': [os.path.join(prefix, 'bin'), os.path.join(prefix, 'lib'),
                     os.path.join(prefix, 'include'), os.path.join(prefix, 'man')]
        }
        super(EB_PGI, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Prefix subdirectories in PGI install dir considered for environment variables defined in module file."""
        dirs = super(EB_PGI, self).make_module_req_guess()
        for key in dirs:
            dirs[key] = [os.path.join(self.install_subdir, d) for d in dirs[key]]

        # $CPATH should not be defined in module for PGI, it causes problems
        # cfr. https://github.com/hpcugent/easybuild-easyblocks/issues/830
        if 'CPATH' in dirs:
            self.log.info("Removing $CPATH entry: %s", dirs['CPATH'])
            del dirs['CPATH']

        return dirs

    def make_module_extra(self):
        """Add environment variables LM_LICENSE_FILE and PGI for license file and PGI location"""
        txt = super(EB_PGI, self).make_module_extra()
        txt += self.module_generator.prepend_paths(self.license_env_var, [self.license_file],
                                                   allow_abs=True, expand_relpaths=False)
        txt += self.module_generator.set_environment('PGI', self.installdir)
        return txt
