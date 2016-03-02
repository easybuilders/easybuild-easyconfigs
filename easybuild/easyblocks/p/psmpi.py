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

        self.correct_mpich_build_env()

        # Bypass the configure_step of EB_MPICH. ParaStationMPI has a completely different set of options. We
        # can't have the same configure_step.
        super(EB_MPICH, self).configure_step()

    # make and make install are default

    def sanity_check_step(self, custom_paths=None, use_new_libnames=None):
        """
        Disable the checking of the launchers for ParaStationMPI
        """
        super(EB_psmpi, self).sanity_check_step(custom_paths=custom_paths,use_new_libnames=use_new_libnames,
                check_launchers=False)
