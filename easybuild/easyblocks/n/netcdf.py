##
# Copyright 2009-2012 Stijn Deweirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
from distutils.version import LooseVersion
from easybuild.framework.application import Application

class NetCDF(Application):
    """Support for building/installing netCDF"""

    def configure(self):
        """Configure build: set config options and configure"""

        self.updatecfg('configopts', "--enable-shared --with-pic ")
        self.updatecfg('configopts', 'FCFLAGS="%s" CC="%s" ' % (self.getenv('$FFLAGS'),
                                                                self.getenv('$MPICC') ))
        
        Application.configure(self)

    def sanitycheck(self):
        """
        Custom sanity check for netCDF
        """
        if not self.getcfg('sanityCheckPaths'):

            incs = ["netcdf.h"]
            libs = ["libnetcdf.so"]
            # since v4.2, the non-C libraries have been split off in seperate packages
            # see netCDF-Fortran and netCDF-C++
            if LooseVersion(self.version) < LooseVersion("4.2"):
                incs += ["netcdf%s" % x for x in ["cpp.h", ".hh", ".inc", ".mod"]] + \
                        ["ncvalues.h", "typesizes.mod"]
                libs += ["libnetcdf_c++.so", "libnetcdff.so"]

            self.setcfg('sanityCheckPaths',{'files':["bin/nc%s" % x for x in ["-config", "copy", "dump",
                                                                              "gen", "gen3"]] +
                                                    ["lib/%s" % x for x in libs] +
                                                    ["include/%s" % x for x in incs],
                                            'dirs':['include']
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)