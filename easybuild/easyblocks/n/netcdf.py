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
EasyBuild support for building and installing netCDF, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os
from distutils.version import LooseVersion

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.cmakemake import CMakeMake
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.modules import get_software_root, get_software_version


class EB_netCDF(CMakeMake):
    """Support for building/installing netCDF"""

    def configure_step(self):
        """Configure build: set config options and configure"""

        if LooseVersion(self.version) < LooseVersion("4.3"):
            self.cfg.update('configopts', "--enable-shared")

            if self.toolchain.options['pic']:
                self.cfg.update('configopts', '--with-pic')

            tup = (os.getenv('FFLAGS'), os.getenv('MPICC'), os.getenv('F90'))
            self.cfg.update('configopts', 'FCFLAGS="%s" CC="%s" FC="%s"' % tup)

            # add -DgFortran to CPPFLAGS when building with GCC
            if self.toolchain.comp_family() == toolchain.GCC:  #@UndefinedVariable
                self.cfg.update('configopts', 'CPPFLAGS="%s -DgFortran"' % os.getenv('CPPFLAGS'))

            ConfigureMake.configure_step(self)

        else:
            hdf5 = get_software_root('HDF5')
            if hdf5:
                env.setvar('HDF5_ROOT', hdf5)

            CMakeMake.configure_step(self)

    def sanity_check_step(self):
        """
        Custom sanity check for netCDF
        """

        incs = ["netcdf.h"]
        libs = ["libnetcdf.so", "libnetcdf.a"]
        # since v4.2, the non-C libraries have been split off in seperate extensions_step
        # see netCDF-Fortran and netCDF-C++
        if LooseVersion(self.version) < LooseVersion("4.2"):
            incs += ["netcdf%s" % x for x in ["cpp.h", ".hh", ".inc", ".mod"]] + \
                    ["ncvalues.h", "typesizes.mod"]
            libs += ["libnetcdf_c++.so", "libnetcdff.so",
                     "libnetcdf_c++.a", "libnetcdff.a"]

        custom_paths = {
                        'files': ["bin/nc%s" % x for x in ["-config", "copy", "dump",
                                                          "gen", "gen3"]] +
                                 ["lib/%s" % x for x in libs] +
                                 ["include/%s" % x for x in incs],
                        'dirs': []
                       }

        super(EB_netCDF, self).sanity_check_step(custom_paths=custom_paths)

def set_netcdf_env_vars(log):
    """Set netCDF environment variables used by other software."""

    netcdf = get_software_root('netCDF')
    if not netcdf:
        log.error("netCDF module not loaded?")
    else:
        env.setvar('NETCDF', netcdf)
        log.debug("Set NETCDF to %s" % netcdf)
        netcdff = get_software_root('netCDF-Fortran')
        netcdf_ver = get_software_version('netCDF')
        if not netcdff:
            if LooseVersion(netcdf_ver) >= LooseVersion("4.2"):
                log.error("netCDF v4.2 no longer supplies Fortran library, also need netCDF-Fortran")
        else:
            env.setvar('NETCDFF', netcdff)
            log.debug("Set NETCDFF to %s" % netcdff)

def get_netcdf_module_set_cmds(log):
    """Get module setenv commands for netCDF."""

    netcdf = os.getenv('NETCDF')
    if netcdf:
        txt = "setenv NETCDF %s\n" % netcdf
        # netCDF-Fortran is optional (only for netCDF v4.2 and later)
        netcdff = os.getenv('NETCDFF')
        if netcdff:
            txt += "setenv NETCDFF %s\n" % netcdff
        return txt
    else:
        log.error("NETCDF environment variable not set?")
