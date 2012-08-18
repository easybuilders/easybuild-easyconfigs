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
EasyBuild support for building and installing HDF5, implemented as an easyblock
"""

import os

from easybuild.framework.application import Application
from easybuild.tools.modules import get_software_root


class eb_HDF5(Application):
    """Support for building/installing HDF5"""

    def configure(self):
        """Configure build: set require config and make options, and run configure script."""

        # configure options
        deps = ["Szip", "zlib"]
        for dep in deps:
            root = get_software_root(dep)
            if root:
                self.updatecfg('configopts', '--with-%s=%s' % (dep.lower(), root))
            else:
                self.log.error("Dependency module %s not loaded." % dep)

        fcomp = 'FC="%s"' % os.getenv('F77')

        self.updatecfg('configopts', "--with-pic --with-pthread --enable-shared")
        self.updatecfg('configopts', "--enable-cxx --enable-fortran %s" % fcomp)

        # MPI and C++ support enabled requires --enable-unsupported, because this is untested by HDF5
        if self.toolkit().opts['usempi']:
            self.updatecfg('configopts', "--enable-unsupported")

        # make options
        self.updatecfg('makeopts', fcomp)

        Application.configure(self)

    # default make and make install are ok

    def sanitycheck(self):
        """
        Custom sanity check for HDF5
        """
        if not self.getcfg('sanityCheckPaths'):

            if self.toolkit().opts['usempi']:
                extra_binaries = ["bin/%s" % x for x in ["h5perf", "h5pcc", "h5pfc", "ph5diff"]]
            else:
                extra_binaries = ["bin/%s" % x for x in ["h5cc", "h5fc"]]

            self.setcfg('sanityCheckPaths',{
                                            'files': ["bin/h5%s" % x for x in ["2gif", "c++", "copy",
                                                                               "debug", "diff", "dump",
                                                                               "import", "jam","ls",
                                                                               "mkgrp", "perf_serial",
                                                                               "redeploy", "repack",
                                                                               "repart", "stat", "unjam"]] +
                                                     ["bin/gif2h5"] + extra_binaries +
                                                     ["lib/libhdf5%s.so" % x for x in ["_cpp", "_fortran",
                                                                                       "_hl_cpp", "_hl",
                                                                                       "hl_fortran", ""]],
                                            'dirs': ['include']
                                           })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
