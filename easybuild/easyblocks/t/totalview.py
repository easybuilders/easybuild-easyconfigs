##
# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2012-2016 Uni.Lu/LCSB, NTUA
# Copyright:: Copyright 2016-2016 Forschungszentrum Juelich
# Authors::   Fotis Georgatos <fotis@cern.ch>
# Authors::   Damian Alvarez  <d.alvarez@fz-juelich.de>
# License::   MIT/GPL
# $Id$
#
# This work implements a part of the HPCBIOS project and is a component of the policy:
# http://hpcbios.readthedocs.org/en/latest/HPCBIOS_06-05.html
##
"""
EasyBuild support for installing Totalview, implemented as an easyblock

@author: Fotis Georgatos (Uni.Lu)
"""
import os

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import find_flexlm_license
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd


class EB_TotalView(EasyBlock):
    """EasyBlock for TotalView"""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for Totalview"""
        super(EB_TotalView, self).__init__(*args, **kwargs)
        
        self.license_file = 'UNKNOWN'
        self.license_env_var = 'UNKNOWN'

    def configure_step(self):
        """
        Handle of license
        """
        default_lic_env_var = 'LM_LICENSE_FILE'
        lic_specs, self.license_env_var = find_flexlm_license(custom_env_vars=[default_lic_env_var],
                                                              lic_specs=[self.cfg['license_file']])

        if lic_specs:
            if self.license_env_var is None:
                self.log.info("Using Totalview license specifications from 'license_file': %s", lic_specs)
                self.license_env_var = default_lic_env_var
            else:
                self.log.info("Using Totalview license specifications from %s: %s", self.license_env_var, lic_specs)

            self.license_file = os.pathsep.join(lic_specs)
            env.setvar(self.license_env_var, self.license_file)

        else:
            raise EasyBuildError("No viable license specifications found; specify 'license_file' or "+
                                 "define $LM_LICENSE_FILE")

    def build_step(self):
        """No building for TotalView."""
        pass

    def install_step(self):
        """Custom install procedure for TotalView."""

        cmd = "./Install -agree -platform linux-x86-64 -nosymlink -install totalview -directory %s" % self.installdir
        run_cmd(cmd)

    def sanity_check_step(self):
        """Custom sanity check for TotalView."""

        binpath_t = 'toolworks/%s.%s/bin/' % (self.name.lower(), self.version) + 'tv%s'

        custom_paths = {
            'files': [binpath_t % i for i in ['8', '8cli', 'dbootstrap', 'dsvr', 'script']],
            'dirs': [],
        }

        super(EB_TotalView, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Specify TotalView custom values for PATH."""
        guesses = super(EB_TotalView, self).make_module_req_guess()

        prefix = os.path.join('toolworks', '%s.%s' % (self.name.lower(), self.version))
        guesses.update({
            'PATH': [os.path.join(prefix, 'bin')],
            'MANPATH': [os.path.join(prefix, 'man')],
        })

        return guesses

    def make_module_extra(self):
        """Add extra environment variables for license file and anything else."""
        txt = super(EB_TotalView, self).make_module_extra()
        txt += self.module_generator.prepend_paths(self.license_env_var, [self.license_file], allow_abs=True, expand_relpaths=False)
        return txt
