##
# Copyright 2013 Ghent University
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
EasyBuild support for building and installing Bowtie, implemented as an easyblock

@author: Cedric Laczny (Uni.Lu)
@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake


class EB_Bowtie(ConfigureMake):
    """
    Support for building bowtie (ifast and sensitive read alignment)
    """

    def configure_step(self):
        """
        Set compilers in makeopts, there is no configure script.
        """
        self.cfg.update('makeopts', 'CC="%s" CPP="%s"' % (os.getenv('CC'), os.getenv('CXX')))

    def install_step(self):
        """
        Install by copying files to install dir
        """
        srcdir = self.cfg['start_dir']
        destdir = os.path.join(self.installdir, 'bin')
        srcfile = None
        try:
            os.makedirs(destdir)
            for filename in ['bowtie-build', 'bowtie', 'bowtie-inspect']:
                srcfile = os.path.join(srcdir, filename)
                shutil.copy2(srcfile, destdir)
        except (IOError, OSError), err:
            self.log.error("Copying %s to installation dir %s failed: %s" % (srcfile, destdir, err))

    def sanity_check_step(self):
        """Custom sanity check for Bowtie."""
        custom_paths = {
            'files': ['bin/bowtie', 'bin/bowtie-build', 'bin/bowtie-inspect'],
            'dirs': []
        }
        super(EB_Bowtie, self).sanity_check_step(custom_paths=custom_paths)
