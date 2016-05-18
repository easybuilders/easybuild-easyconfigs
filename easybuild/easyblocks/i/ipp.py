##
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
##
"""
EasyBuild support for installing the Intel Performance Primitives (IPP) library, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Lumir Jasiok (IT4Innovations)
"""

from distutils.version import LooseVersion
import os

from easybuild.easyblocks.generic.intelbase import IntelBase, ACTIVATION_NAME_2012, LICENSE_FILE_NAME_2012
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.systemtools import get_platform_name
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_ipp(IntelBase):
    """
    Support for installing Intel Integrated Performance Primitives library
    """
    def install_step(self):
        """
        Actual installation
        - create silent cfg file
        - execute command
        """

        platform_name = get_platform_name()
        if platform_name.startswith('x86_64'):
            self.arch = "intel64"
        elif platform_name.startswith('i386') or platform_name.startswith('i686'):
            self.arch = 'ia32'
        else:
            raise EasyBuildError("Failed to determine system architecture based on %s", platform_name)

        silent_cfg_names_map = None
        silent_cfg_extras = None

        if LooseVersion(self.version) < LooseVersion('8.0'):
            silent_cfg_names_map = {
                'activation_name': ACTIVATION_NAME_2012,
                'license_file_name': LICENSE_FILE_NAME_2012,
            }

        # in case of IPP 9.x, we have to specify ARCH_SELECTED in silent.cfg
        if LooseVersion(self.version) >= LooseVersion('9.0'):
            silent_cfg_extras = {
                'ARCH_SELECTED': self.arch.upper()
            }

        super(EB_ipp, self).install_step(silent_cfg_names_map=silent_cfg_names_map, silent_cfg_extras=silent_cfg_extras)

    def sanity_check_step(self):
        """Custom sanity check paths for IPP."""
        shlib_ext = get_shared_lib_ext()

        if LooseVersion(self.version) < LooseVersion('8.0'):
            dirs = ['compiler/lib/intel64', 'ipp/bin', 'ipp/include',
                    'ipp/interfaces/data-compression', 'ipp/tools/intel64']
        elif LooseVersion(self.version) >= LooseVersion('9.0'):
            dirs = ['ipp/bin', 'ipp/include', 'ipp/tools/intel64']
        else:
            dirs = ['composerxe/lib/intel64', 'ipp/bin', 'ipp/include',
                    'ipp/tools/intel64']

        ipp_libs = ['cc', 'ch', 'core', 'cv', 'dc', 'i', 's', 'vm']
        if LooseVersion(self.version) < LooseVersion('9.0'):
            ipp_libs.extend(['ac', 'di', 'j', 'm', 'r', 'sc', 'vc'])

        custom_paths = {
            'files': ['ipp/lib/intel64/libipp%s' % y for x in ipp_libs for y in ['%s.a' % x, '%s.%s' % (x, shlib_ext)]],
            'dirs': dirs,
        }

        super(EB_ipp, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for
        """
        guesses = super(EB_ipp, self).make_module_req_guess()

        if LooseVersion(self.version) >= LooseVersion('9.0'):
            lib_path = os.path.join('lib', self.arch)
            include_path = 'ipp/include'

            guesses.update({
                'LD_LIBRARY_PATH': [lib_path],
                'LIBRARY_PATH': [lib_path],
                'CPATH': [include_path],
                'INCLUDE': [include_path],
            })

        return guesses
