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

from easybuild.framework.application import Application


class EB_Hypre(Application):
    """Support for building Hypre."""

    def configure(self):
        """Configure Hypre build after setting extra configure options."""

        self.updatecfg('configopts', '--with-MPI-include=%s' % os.getenv('MPI_INC_DIR'))

        for dep in ["BLAS", "LAPACK"]:
            libs = ' '.join(os.getenv('%s_STATIC_LIBS' % dep).split(','))
            self.updatecfg('configopts', '--with-%s-libs="%s"' % (dep.lower(), libs))
            self.updatecfg('configopts', '--with-%s-lib-dirs="%s"' % (dep.lower(),
                                                                      os.getenv('%s_LIB_DIR' % dep)))

        Application.configure(self)

    def sanitycheck(self):
        """Custom sanity check for Hypre."""

        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths', {
                                             'files':['lib/libHYPRE.a'],
                                             'dirs':['include']
                                             })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)