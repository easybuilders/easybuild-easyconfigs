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
EasyBuild support for Mothur, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""

import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.modules import get_software_root


class EB_Mothur(ConfigureMake):
    """Support for building and installing Mothur."""

    def __init__(self, *args, **kwargs):
        """Custom easyblock initialisation for Mothur."""
        super(EB_Mothur, self).__init__(*args, **kwargs)

        # set correct start dir
        self.cfg['start_dir'] = '%s.%s' % (self.name, self.version)

    def configure_step(self, cmd_prefix=''):
        """Configure Mothur build by setting make options."""
        # Fortran compiler and options
        self.cfg.update('makeopts', 'FORTAN_COMPILER="%s" FORTRAN_FLAGS="%s"' % (os.getenv('F77'), os.getenv('FFLAGS')))
        # enable 64-bit build
        if not self.toolchain.options['32bit']:
            self.cfg.update('makeopts', '64BIT_VERSION=yes')
        # enable readline support
        if get_software_root('libreadline') and get_software_root('ncurses'):
            self.cfg.update('makeopts', 'USEREADLINE=yes')
        # enable MPI support
        if self.toolchain.options.get('usempi', None):
            self.cfg.update('makeopts', 'USEMPI=yes CXX="%s"' % os.getenv('MPICXX'))
            self.cfg.update('premakeopts', 'CXXFLAGS="$CXXFLAGS -DMPICH_IGNORE_CXX_SEEK"')
        # enable compression
        if get_software_root('bzip2') or get_software_root('gzip'):
            self.cfg.update('makeopts', 'USE_COMPRESSION=yes')

    def install_step(self):
        """
        Install by copying files to install dir
        """
        srcdir = os.path.join(self.builddir, self.cfg['start_dir'])
        destdir = os.path.join(self.installdir, 'bin')
        srcfile = None
        try:
            os.makedirs(destdir)
            for filename in ['mothur', 'uchime']:
                srcfile = os.path.join(srcdir, filename)
                shutil.copy2(srcfile, destdir)
        except OSError, err:
            self.log.error("Copying %s to installation dir %s failed: %s", srcfile, destdir, err)

    def sanity_check_step(self):
        """Custom sanity check for Mothur."""
        custom_paths = {
            'files': ["bin/mothur"],
            'dirs': [],
        }

        super(EB_Mothur, self).sanity_check_step(custom_paths=custom_paths)

