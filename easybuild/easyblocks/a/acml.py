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
EasyBuild support for AMD Core Math Library (ACML), implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os
from distutils.version import LooseVersion

from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.run import run_cmd_qa
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_ACML(EasyBlock):

    @staticmethod
    def extra_options():
        extra_vars = {
            'use_fma4': [False, "Use library with FMA support.", CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Constructor, adds extra class variables."""
        super(EB_ACML, self).__init__(*args, **kwargs)

        # determine base directory and suffix for ACML installation
        vsuff_list = self.cfg['versionsuffix'].split('-')
        self.basedir = ''
        if len(vsuff_list) >= 3:
            comp = vsuff_list[1]  # gfortran, ifort, ...
            bits = vsuff_list[2]  # 32bit or 64bit
            self.basedir += comp + bits[:2]
        # specialized suffix, e.g., _fma4 for fused multiply-add
        if LooseVersion(self.version) >= LooseVersion("5") and self.cfg['use_fma4']:
            self.basedir += '_fma4'

        self.suffix = ''
        if self.cfg['versionsuffix'].split('-')[-1] == "int64":
            self.suffix = '_int64'

    def configure_step(self):
        """No custom configure step for ACML."""
        pass

    def build_step(self):
        """No custom build step for ACML."""
        pass

    def install_step(self):
        """Install by running install script."""

        altver = '-'.join(self.version.split('.'))
        cmd = "./install-%s-%s%s.sh -accept" % (self.name.lower(), altver, self.cfg['versionsuffix'])

        qa = {'The directory will be created if it does not already exist. >': self.installdir}

        run_cmd_qa(cmd, qa, log_all=True, simple=True)

    def make_module_extra(self):
        """Add extra entries in module file (various paths)."""

        txt = super(EB_ACML, self).make_module_extra()

        basepaths = ["%s%s" % (self.basedir, self.suffix),
                     "%s_mp%s" % (self.basedir, self.suffix)]

        txt += self.module_generator.set_environment('ACML_BASEDIR', basepaths[0])
        txt += self.module_generator.set_environment('ACML_BASEDIR_MT', basepaths[1])

        for key in ['CPATH', 'FPATH']:
            for path in basepaths:
                txt += self.module_generator.prepend_paths(key, os.path.join(path, 'include'))

        for key in ['LD_LIBRARY_PATH', 'LIBRARY_PATH']:
            for path in basepaths:
                txt += self.module_generator.prepend_paths(key, os.path.join(path, 'lib'))

        return txt

    def sanity_check_step(self):
        """Custom sanity check for ACML."""

        inc_extra = []
        lib_extra = []
        if LooseVersion(self.version) < LooseVersion("5"):
            inc_extra = ['_mv', '_mv_m128']
            lib_extra = ['_mv']

        inc_files = []
        lib_files = []
        for suff in ['', '_mp']:

            fp = "%s%s%s" % (self.basedir, suff, self.suffix)
            for inc in [''] + inc_extra:
                inc_files.append(os.path.join(fp, 'include', 'acml%s.h' % inc))

            for lib in [suff] + lib_extra:
                for ext in ['a', get_shared_lib_ext()]:
                    lib_files.append(os.path.join(fp, 'lib', 'libacml%s.%s' % (lib, ext)))

        custom_paths = {
            'files': ['util/cpuid.exe'] + inc_files + lib_files,
            'dirs': [],
        }
        super(EB_ACML, self).sanity_check_step(custom_paths=custom_paths)
