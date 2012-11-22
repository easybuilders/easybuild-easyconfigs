##
# Copyright 2009-2012 Ghent University
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
#
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
##
"""
EasyBuild support for AMD Core Math Library (ACML), implemented as an easyblock
"""

import os
from distutils.version import LooseVersion

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import run_cmd_qa


class EB_ACML(EasyBlock):

    def __init__(self, *args, **kwargs):
        """Constructor, adds extra class variables."""

        super(EB_ACML, self).__init__(*args, **kwargs)

        vsuff_list = self.cfg['versionsuffix'].split('-')

        comp = vsuff_list[1]
        bits = vsuff_list[2]
        self.basedir = None
        if bits == "32bit":
            self.basedir = "%s32" % comp
        elif bits == "64bit":
            self.basedir = "%s64" % comp
        else:
            self.log.error("Unexpected 'bits' entry in versionsuffix[2]: %s" % bits)

        self.suffix = ''
        if self.cfg['versionsuffix'].split('-')[-1] == "int64":
            self.suffix = '_int64'

        self.altlib = '_mp'
        if LooseVersion(self.version) >= LooseVersion("5"):
            self.altlib = '_fma4'

    def configure_step(self):
        """No configure."""
        pass

    def build_step(self):
        """No build."""
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

        basepaths = ["%s%s" % (self.basedir, self.suffix), "%s%s%s" % (self.basedir, self.altlib, self.suffix)]

        for key in ['CPATH', 'FPATH']:
            for path in basepaths:
                txt += self.moduleGenerator.prepend_paths(key, os.path.join(path, 'include'))

        for key in ['LD_LIBRARY_PATH', 'LIBRARY_PATH']:
            for path in basepaths:
                txt += self.moduleGenerator.prepend_paths(key, os.path.join(path, 'lib'))

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
        for suff in ['', self.altlib]:

            fp = "%s%s" % (self.basedir, suff)
            for inc in [''] + inc_extra:
                inc_files.append(os.path.join(fp, 'include', 'acml%s.h' % inc))

            # _mp is appended to libs, _fma4 is not
            if suff in "_fma4":
                suff = ''
            for lib in [suff] + lib_extra:
                for ext in ['.a', '.so']:
                    lib_files.append(os.path.join(fp, 'lib', 'libacml%s%s' % (lib, ext)))

        custom_paths = {
                        'files':['util/cpuid.exe'] + inc_files + lib_files,
                        'dirs':[]
                       }

        super(EB_ACML, self).sanity_check_step(custom_paths=custom_paths)
