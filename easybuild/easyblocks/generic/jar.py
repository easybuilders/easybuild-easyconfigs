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
EasyBuild support for JAR files, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import shutil

from easybuild.easyblocks.generic.binary import Binary


class JAR(Binary):
    """Support for installing JAR files."""

    def install_step_xxx(self):
        """Custom installation for JAR files: just copy them to install path."""

        for srcfile in self.src:
            shutil.copy(srcfile['path'], self.installdir)

    def make_module_extra(self):
        """Extra module entries for JAR files: CLASSPATH."""

        txt = super(JAR, self).make_module_extra()

        for srcfile in self.src:
            srcname = srcfile['name']

            self.log.debug('Checking %s...' % srcname)

            if srcname.endswith('.jar'):
                self.log.debug('Adding %s to classpath' % srcname)
                txt += self.module_generator.prepend_paths('CLASSPATH', [srcname])

        return txt
