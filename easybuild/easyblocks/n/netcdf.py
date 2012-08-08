##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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
EasyBuild support for building and installing netCDF, implemented as an easyblock
"""

import os
from distutils.version import LooseVersion

import easybuild.tools.environment as env
import easybuild.tools.toolkit as toolkit
from easybuild.framework.application import Application
from easybuild.tools.modules import get_software_root, get_software_version


class NetCDF(Application):
    """Support for building/installing netCDF"""

    def configure(self):
        """Configure build: set config options and configure"""

        self.updatecfg('configopts', "--enable-shared")

        if self.toolkit().opts['pic']:
            self.updatecfg('configopts', '--with-pic')

        self.updatecfg('configopts', 'FCFLAGS="%s" CC="%s" FC="%s"' % (os.getenv('FFLAGS'),
                                                                       os.getenv('MPICC'),
                                                                       os.getenv('F90')
                                                                      ))

        # add -DgFortran to CPPFLAGS when building with GCC
        if self.toolkit().comp_family() == toolkit.GCC:
            env.set('CPPFLAGS', "%s -DgFortran" % os.getenv('CPPFLAGS'))

        Application.configure(self)

    def sanitycheck(self):
        """
        Custom sanity check for netCDF
        """
        if not self.getcfg('sanityCheckPaths'):

            incs = ["netcdf.h"]
            libs = ["libnetcdf.so", "libnetcdf.a"]
            # since v4.2, the non-C libraries have been split off in seperate packages
            # see netCDF-Fortran and netCDF-C++
            if LooseVersion(self.version()) < LooseVersion("4.2"):
                incs += ["netcdf%s" % x for x in ["cpp.h", ".hh", ".inc", ".mod"]] + \
                        ["ncvalues.h", "typesizes.mod"]
                libs += ["libnetcdf_c++.so", "libnetcdff.so",
                         "libnetcdf_c++.a", "libnetcdff.a"]

            self.setcfg('sanityCheckPaths',{
                                            'files': ["bin/nc%s" % x for x in ["-config", "copy", "dump",
                                                                              "gen", "gen3"]] +
                                                     ["lib/%s" % x for x in libs] +
                                                     ["include/%s" % x for x in incs],
                                            'dirs': []
                                           })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)

def set_netcdf_env_vars(log):
    """Set netCDF environment variables used by other software."""

    netcdf = get_software_root('netCDF')
    if not netcdf:
        log.error("netCDF module not loaded?")
    else:
        env.set('NETCDF', netcdf)
        log.debug("Set NETCDF to %s" % netcdf)
        netcdff = get_software_root('netCDF-Fortran')
        netcdf_ver = get_software_version('netCDF')
        if not netcdff:
            if LooseVersion(netcdf_ver) >= LooseVersion("4.2"):
                log.error("netCDF v4.2 no longer supplies Fortran library, also need netCDF-Fortran")
        else:
            env.set('NETCDFF', netcdff)
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
