##
# Copyright 2016-2016 Ghent University, Forschungszentrum Juelich
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
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
EasyBuild support for building and installing the ParaStationMPI library, implemented as an easyblock

@author: Damian Alvarez (Forschungszentrum Juelich)
"""
import os
from distutils.version import LooseVersion

from easybuild.easyblocks.mpich import EB_MPICH
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_psmpi(EB_MPICH):
    """
    Support for building the ParaStationMPI library.
    - some compiler dependent configure options
    """

    def configure_step(self):
        """
        Custom configuration procedure for ParaStationMPI
        * unset environment variables that leak into mpi* wrappers, and define $MPICHLIB_* equivalents instead
        """

        # things might go wrong if a previous install dir is present, so let's get rid of it
        if not self.cfg['keeppreviousinstall']:
            self.log.info("Making sure any old installation is removed before we start the build...")
            super(EB_psmpi, self).make_dir(self.installdir, True, dontcreateinstalldir=True)

        # MPICH configure script complains when F90 or F90FLAGS are set,
        # they should be replaced with FC/FCFLAGS instead.
        # Additionally, there are a set of variables (FCFLAGS among them) that should not be set at configure time,
        # or they will leak in the mpix wrappers.
        # Specific variables to be included in the wrapper exists, but they changed between MPICH 3.1.4 and MPICH 3.2
        # and in a typical scenario we probably don't want them.
        self.setup_env_vars()

        # Bypass the configure_step of EB_MPICH
        super(EB_MPICH, self).configure_step()

    # make and make install are default

    def sanity_check_step(self, custom_paths=None, use_new_libnames=None):
        """
        Custom sanity check for ParaStationMPI
        """
        shlib_ext = get_shared_lib_ext()
        if custom_paths is None:
            custom_paths = {}

        if use_new_libnames is None:
            # cfr. http://git.mpich.org/mpich.git/blob_plain/v3.1.1:/CHANGES
            # MPICH changed its library names sinceversion 3.1.1
            use_new_libnames = LooseVersion(self.version) >= LooseVersion('5.1.0-1')

        # Starting MPICH 3.1.1, libraries have been renamed
        # cf http://git.mpich.org/mpich.git/blob_plain/v3.1.1:/CHANGES
        if use_new_libnames:
            libnames = ['mpi', 'mpicxx', 'mpifort']
        else:
            libnames = ['fmpich', 'mpichcxx', 'mpichf90', 'mpich', 'mpl', 'opa']

        binaries = ['mpicc', 'mpicxx', 'mpif77', 'mpif90']
        bins = [os.path.join('bin', x) for x in binaries]
        headers = [os.path.join('include', x) for x in ['mpi.h', 'mpicxx.h', 'mpif.h']]
        libs = [os.path.join('lib', 'lib%s.%s' % (l, e)) for l in libnames for e in ['a', shlib_ext]]

        custom_paths.setdefault('dirs', []).extend(['bin', 'include', 'lib'])
        custom_paths.setdefault('files', []).extend(bins + headers + libs)

        # Bypass the sanity_check_step of EB_MPICH
        super(EB_MPICH, self).sanity_check_step(custom_paths=custom_paths)
