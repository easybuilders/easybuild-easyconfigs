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
import os
from easybuild.framework.application import Application

class HDF5(Application):
    """Support for building/installing HDF5"""

    def configure(self):
        """Configure build: set require config and make options, and run configure script."""

        # configure options
        deps = ["Szip", "zlib"]
        for dep in deps:
            if os.getenv('SOFTROOT%s' % dep.upper()):
                self.updatecfg('configopts', '--with-%s=$SOFTROOT%s' % (dep.lower(), dep.upper()))
            else:
                self.log.error("Dependency module %s not loaded." % dep)

        fcomp = "FC=%s" % os.getenv('F77')

        self.updatecfg('configopts', "--enable-cxx --enable-fortran %s" % fcomp)
        self.updatecfg('configopts', "--with-pic --with-pthread --enable-shared")

        # make options
        self.updatecfg('makeopts', fcomp)

        Application.configure(self)

    # default make and make install are ok

    def sanitycheck(self):
        """
        Custom sanity check for HDF5
        """
        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths',{'files':["bin/h5%s" % x for x in ["2gif", "c++", "cc",
                                                                              "copy", "debug", "diff",
                                                                              "dump", "fc", "import",
                                                                              "jam","ls", "mkgrp",
                                                                              "perf_serial", "redeploy",
                                                                              "repack", "repart", "stat",
                                                                              "unjam"]] +
                                                    ["bin/gif2h5"] +
                                                    ["lib/libhdf5%s.so" % x for x in ["_cpp", "_fortran",
                                                                                      "_hl_cpp", "_hl",
                                                                                      "hl_fortran", ""]],
                                            'dirs':['include']
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)