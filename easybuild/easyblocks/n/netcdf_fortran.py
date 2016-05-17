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
EasyBuild support for building and installing netCDF-Fortran, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_netCDF_minus_Fortran(ConfigureMake):
    """Support for building/installing the netCDF-Fortran library"""

    def configure_step(self):
        """Configure build: set config options and configure"""

        if self.toolchain.options['pic']:
            self.cfg.update('configopts', "--with-pic")

        self.cfg.update('configopts', 'FCFLAGS="%s" FC="%s"' % (os.getenv('FFLAGS'), os.getenv('F90')))

        # add -DgFortran to CPPFLAGS when building with GCC
        if self.toolchain.comp_family() == toolchain.GCC:  #@UndefinedVariable
            env.setvar('CPPFLAGS', "%s -DgFortran" % os.getenv('CPPFLAGS'))

        super(EB_netCDF_minus_Fortran, self).configure_step()

    def sanity_check_step(self):
        """
        Custom sanity check for netCDF-Fortran
        """
        shlib_ext = get_shared_lib_ext()
        custom_paths = {
            'files': ["bin/nf-config"] + ["lib/libnetcdff.%s" % x for x in ['a', shlib_ext]] +
                     ["include/%s" % x for x in ["netcdf.inc", "netcdf.mod", "typesizes.mod"]],
            'dirs': [],
        }
        super(EB_netCDF_minus_Fortran, self).sanity_check_step(custom_paths=custom_paths)
