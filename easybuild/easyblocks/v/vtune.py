# #
# Copyright 2013 Ghent University
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
EasyBuild support for installing Intel VTune, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.intelbase import IntelBase, ACTIVATION_NAME_2012, LICENSE_FILE_NAME_2012


class EB_VTune(IntelBase):
    """
    Support for installing Intel VTune
    """
    def install_step(self):
        """
        Actual installation
        - create silent cfg file
        - execute command
        """
        silent_cfg_names_map = None

        if LooseVersion(self.version) <= LooseVersion('2013_update10'):
            silent_cfg_names_map = {
                'activation_name': ACTIVATION_NAME_2012,
                'license_file_name': LICENSE_FILE_NAME_2012,
            }

        super(EB_VTune, self).install_step(silent_cfg_names_map=silent_cfg_names_map)

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for
        """

        guesses = super(EB_VTune, self).make_module_req_guess()

        if self.cfg['m32']:
            guesses.update({
                'PATH': ['bin32'],
                'LD_LIBRARY_PATH': ['lib32'],
                'LIBRARY_PATH': ['lib32'],
            })
        else:
            guesses.update({
                'PATH': ['bin64'],
                'LD_LIBRARY_PATH': ['lib64'],
                'LIBRARY_PATH': ['lib64'],
            })

        guesses.update({
            'CPATH': ['include'],
            'FPATH': ['include'],
            'MANPATH': ['man'],
        })

        return guesses

    def sanity_check_step(self):
        """Custom sanity check paths for Intel VTune."""

        binaries = ['amplxe-cl', 'amplxe-configurator', 'amplxe-feedback', 'amplxe-gui', 'amplxe-runss']
        if self.cfg['m32']:
            files = ["bin32/%s" % x for x in binaries]
            dirs = ["lib32", "include"]
        else:
            files = ["bin64/%s" % x for x in binaries]
            dirs = ["lib64", "include"]

        custom_paths = {
                        'files': files,
                        'dirs': dirs,
                       }

        super(EB_VTune, self).sanity_check_step(custom_paths=custom_paths)
