##
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
##
"""
EasyBuild support for Mothur, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import glob
import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root


class EB_Mothur(ConfigureMake):
    """Support for building and installing Mothur."""

    def guess_start_dir(self):
        """Set correct start directory."""
        # Mothur zip files tend to contain multiple directories next to the actual source dir (e.g. __MACOSX),
        # so the default start directory guess is most likely incorrect
        mothur_dirs = glob.glob(os.path.join(self.builddir, 'Mothur.*'))
        if len(mothur_dirs) == 1:
            self.cfg['start_dir'] = mothur_dirs[0]
        elif len(os.listdir(self.builddir)) > 1:
            # we only have an issue if the default guessing approach will not work
            raise EasyBuildError("Failed to guess start directory from %s", mothur_dirs)

        super(EB_Mothur, self).guess_start_dir()

    def configure_step(self, cmd_prefix=''):
        """Configure Mothur build by setting make options."""
        # Fortran compiler and options
        self.cfg.update('buildopts', 'FORTAN_COMPILER="%s" FORTRAN_FLAGS="%s"' % (os.getenv('F77'), os.getenv('FFLAGS')))
        # enable 64-bit build
        if not self.toolchain.options['32bit']:
            self.cfg.update('buildopts', '64BIT_VERSION=yes')
        # enable readline support
        if get_software_root('libreadline') and get_software_root('ncurses'):
            self.cfg.update('buildopts', 'USEREADLINE=yes')
        # enable MPI support
        if self.toolchain.options.get('usempi', None):
            self.cfg.update('buildopts', 'USEMPI=yes CXX="%s"' % os.getenv('MPICXX'))
            self.cfg.update('prebuildopts', 'CXXFLAGS="$CXXFLAGS -DMPICH_IGNORE_CXX_SEEK"')
        # enable compression
        if get_software_root('bzip2') or get_software_root('gzip'):
            self.cfg.update('buildopts', 'USE_COMPRESSION=yes')

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
            raise EasyBuildError("Copying %s to installation dir %s failed: %s", srcfile, destdir, err)

    def sanity_check_step(self):
        """Custom sanity check for Mothur."""
        custom_paths = {
            'files': ["bin/mothur"],
            'dirs': [],
        }

        super(EB_Mothur, self).sanity_check_step(custom_paths=custom_paths)

