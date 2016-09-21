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
EasyBuild support for building and installing HDF5, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.systemtools import get_shared_lib_ext

class EB_HDF5(ConfigureMake):
    """Support for building/installing HDF5"""

    def configure_step(self):
        """Configure build: set require config and make options, and run configure script."""

        # configure options for dependencies
        deps = [
            ("Szip", "--with-szlib"),
            ("zlib", "--with-zlib"),
        ]
        for (dep, opt) in deps:
            root = get_software_root(dep)
            if root:
                self.cfg.update('configopts', '%s=%s' % (opt, root))
            else:
                raise EasyBuildError("Dependency module %s not loaded.", dep)

        fcomp = 'FC="%s"' % os.getenv('F90')

        self.cfg.update('configopts', "--with-pic --with-pthread --enable-shared")
        self.cfg.update('configopts', "--enable-cxx --enable-fortran %s" % fcomp)

        # MPI and C++ support enabled requires --enable-unsupported, because this is untested by HDF5
        # also returns False if MPI is not supported by this toolchain
        if self.toolchain.options.get('usempi', None):
            self.cfg.update('configopts', "--enable-unsupported --enable-parallel")
        else:
            self.cfg.update('configopts', "--disable-parallel")

        # make options
        self.cfg.update('buildopts', fcomp)

        # set RUNPARALLEL if MPI is not enabled (or not supported by this toolchain)
        if self.toolchain.options.get('usempi', None):
            env.setvar('RUNPARALLEL', 'mpirun -np \$\${NPROCS:=2}')

        super(EB_HDF5, self).configure_step()

    # default make and make install are ok

    def sanity_check_step(self):
        """
        Custom sanity check for HDF5
        """

        # also returns False if MPI is not supported by this toolchain
        if self.toolchain.options.get('usempi', None):
            extra_binaries = ["bin/%s" % x for x in ["h5perf", "h5pcc", "h5pfc", "ph5diff"]]
        else:
            extra_binaries = ["bin/%s" % x for x in ["h5cc", "h5fc"]]

        libs = ['', '_cpp', '_fortran', '_hl_cpp', '_hl', 'hl_fortran']
        shlib_ext = get_shared_lib_ext()
        custom_paths = {
            'files': ["bin/h5%s" % x for x in ["2gif", "c++", "copy", "debug", "diff",
                                               "dump", "import", "jam","ls", "mkgrp",
                                               "perf_serial", "redeploy", "repack",
                                               "repart", "stat", "unjam"]] +
                     ["bin/gif2h5"] + extra_binaries +
                     ["lib/libhdf5%s.%s" % (l, shlib_ext) for l in libs],
            'dirs': ['include'],
        }
        super(EB_HDF5, self).sanity_check_step(custom_paths=custom_paths)
