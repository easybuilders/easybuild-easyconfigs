##
# Copyright 2013 Ghent University
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
EasyBuild support for building and installing ESMF, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import BUILD
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_ESMF(ConfigureMake):
    """Support for building/installing ESMF."""

    def configure_step(self):
        """Custom configuration procedure for ESMF through environment variables."""

        env.setvar('ESMF_DIR', self.cfg['start_dir'])
        env.setvar('ESMF_INSTALL_PREFIX', self.installdir)
        env.setvar('ESMF_INSTALL_BINDIR', 'bin')
        env.setvar('ESMF_INSTALL_LIBDIR', 'lib')
        env.setvar('ESMF_INSTALL_MODDIR', 'mod')

        # specify compiler
        comp_family = self.toolchain.comp_family()
        if comp_family in [toolchain.GCC]:
            compiler = 'gfortran'
        else:
            compiler = comp_family.lower()
        env.setvar('ESMF_COMPILER', compiler)

        # specify MPI communications library
        comm = None
        mpi_family = self.toolchain.mpi_family()
        if mpi_family in [toolchain.MPICH, toolchain.QLOGICMPI]:
            # MPICH family for MPICH v3.x, which is MPICH2 compatible
            comm = 'mpich2'
        else:
            comm = mpi_family.lower()
        env.setvar('ESMF_COMM', comm)

        # specify decent LAPACK lib
        env.setvar('ESMF_LAPACK', 'user')
        env.setvar('ESMF_LAPACK_LIBS', '%s %s' % (os.getenv('LDFLAGS'), os.getenv('LIBLAPACK_MT')))

        # specify netCDF
        netcdf = get_software_root('netCDF')
        if netcdf:
            env.setvar('ESMF_NETCDF', 'user')
            netcdf_libs = ['-L%s/lib' % netcdf, '-lnetcdf']

            # Fortran
            netcdff = get_software_root('netCDF-Fortran')
            if netcdff:
                netcdf_libs = ["-L%s/lib" % netcdff] + netcdf_libs + ["-lnetcdff"]
            else:
                netcdf_libs.append('-lnetcdff')

            # C++
            netcdfcxx = get_software_root('netCDF-C++')
            if netcdfcxx:
                netcdf_libs = ["-L%s/lib" % netcdfcxx] + netcdf_libs + ["-lnetcdf_c++"]
            else:
                netcdf_libs.append('-lnetcdf_c++')

            env.setvar('ESMF_NETCDF_LIBS', ' '.join(netcdf_libs))

        # 'make info' provides useful debug info
        cmd = "make info"
        run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def sanity_check_step(self):
        """Custom sanity check for ESMF."""
        shlib_ext = get_shared_lib_ext()

        custom_paths = {
            'files':
                [os.path.join('bin', x) for x in ['ESMF_Info', 'ESMF_InfoC', 'ESMF_RegridWeightGen', 'ESMF_WebServController']] +
                [os.path.join('lib', x) for x in ['libesmf.a', 'libesmf.%s' % shlib_ext]],
            'dirs': ['include', 'mod'],
        }

        super(EB_ESMF, self).sanity_check_step(custom_paths=custom_paths)
