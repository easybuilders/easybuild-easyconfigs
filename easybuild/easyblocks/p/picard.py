##
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
##
"""
Support for building and installing picard, implemented as an easyblock.

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os
import re
import shutil

from easybuild.framework.easyblock import EasyBlock


class EB_picard(EasyBlock):
    """Support for building and installing picard."""

    def configure_step(self):
        """No configure step for picard"""
        pass

    def build_step(self):
        """No build step for picard"""
        pass

    def install_step(self):
        """Install picard by copying required files"""
        # recent version may contain more than just the picard-tools subdirectory
        picard_tools_dir = 'picard-tools-%s' % self.version
        if not re.search("%s/?$" % picard_tools_dir, self.cfg['start_dir']):
            self.cfg['start_dir'] = os.path.join(self.cfg['start_dir'], picard_tools_dir)
            if not os.path.exists(self.cfg['start_dir']):
                self.log.error("Path %s to copy files from doesn't exist." % self.cfg['start_dir'])

        for jar in os.listdir(self.cfg['start_dir']):
            src = os.path.join(self.cfg['start_dir'], jar)
            dst = os.path.join(self.installdir, jar)
            try:
                shutil.copy2(src, dst)
                self.log.info("Successfully copied %s to %s" % (src, dst))
            except OSError, err:
                self.log.error("Failed to copy %s to %s (%s)" % (src, dst, err))

    def sanity_check_step(self):
        """Custom sanity check for picard"""
        custom_paths = {
            'files': ["%s-%s.jar" % (x, self.version) for x in ['picard', 'sam']],
            'dirs': [],
        }
        super(EB_picard, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Add module entries specific to picard"""
        txt = super(EB_picard, self).make_module_extra()
        txt += self.moduleGenerator.prepend_paths('PATH', '')
        return txt
