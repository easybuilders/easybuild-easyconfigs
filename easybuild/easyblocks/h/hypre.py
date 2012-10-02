# Copyright 2012 Kenneth Hoste
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
EasyBuild support for Hypre, implemented as an easyblock
"""
import os

from easybuild.easyblocks.configuremake import EB_ConfigureMake  #@UnresolvedImport


class EB_Hypre(EB_ConfigureMake):
    """Support for building Hypre."""

    def configure_step(self):
        """Configure Hypre build after setting extra configure options."""

        self.cfg.update('configopts', '--with-MPI-include=%s' % os.getenv('MPI_INC_DIR'))

        for dep in ["BLAS", "LAPACK"]:
            libs = ' '.join(os.getenv('%s_STATIC_LIBS' % dep).split(','))
            self.cfg.update('configopts', '--with-%s-libs="%s"' % (dep.lower(), libs))
            self.cfg.update('configopts', '--with-%s-lib-dirs="%s"' % (dep.lower(),
                                                                      os.getenv('%s_LIB_DIR' % dep)))

        super(self.__class__, self).configure_step()

    def sanity_check_step(self):
        """Custom sanity check for Hypre."""

        custom_paths = {
                        'files':['lib/libHYPRE.a'],
                        'dirs':['include']
                       }

        super(self.__class__, self).sanity_check_step(custom_paths=custom_paths)
