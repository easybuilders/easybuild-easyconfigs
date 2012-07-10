##
# Copyright 2009-2012 Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
from easybuild.easyblocks.c.cmakepythonpackage import CMakePythonPackage
from easybuild.tools.modules import get_software_root

class DOLFIN(CMakePythonPackage):
    """Extension of the CMakePythonPackage for Dolfin.
    
    Dolfin needs some environment variables to be set at run time.
    """

    def configure(self):
        """Configure Dolfin build."""

        # make sure that required dependencies are loaded
        deps = ['Armadillo', 'Boost', 'ParMETIS', 'Python', 'SCOTCH', 'SuiteSparse', 'UFC']
        depsdict = {}
        for dep in deps:
            deproot = get_software_root(dep)
            if not deproot:
                self.log.error("Dependency %s not available." % dep)
            else:
                depsdict.update({dep:deproot})

        # run cmake in debug mode
        self.updatecfg('configopts', ' -DCMAKE_BUILD_TYPE=Debug')

        # set correct compilers to be used at runtime
        self.updatecfg('configopts', ' -DMPI_C_COMPILER="$MPICC"')
        self.updatecfg('configopts', ' -DMPI_CXX_COMPILER="$MPICXX"')

        # Boost config parameters
        self.updatecfg('configopts', " -DBOOST_INCLUDEDIR=%s/include" % depsdict['Boost'])
        self.updatecfg('configopts', " -DBoost_DEBUG=ON -DBOOST_ROOT=%s" % depsdict['Boost'])

        # UFC and Armadillo config params
        self.updatecfg('configopts', " -DUFC_DIR=%s" % depsdict['UFC'])
        self.updatecfg('configopts', "-DARMADILLO_DIR:PATH=%s " % depsdict['Armadillo'])

        # specify MPI library
        self.updatecfg('configopts', ' -DMPI_COMPILER="%s"' % os.getenv('MPICC'))

        if  os.getenv('MPI_LIB_SHARED') and os.getenv('MPI_INC'):
            self.updatecfg('configopts', ' -DMPI_LIBRARY="%s"' % os.getenv('MPI_LIB_SHARED'))
            self.updatecfg('configopts', ' -DMPI_INCLUDE_PATH="%s"' % os.getenv('MPI_INC'))
        else:
            self.log.error('MPI_LIB_SHARED or MPI_INC not set, could not determine MPI-related paths.')

        # specify Python paths
        python_short_ver = ".".join(os.getenv('SOFTVERSIONPYTHON').split(".")[0:2])
        self.updatecfg('configopts', " -DPYTHON_INCLUDE_PATH=%s/include/python%s" % (depsdict['Python'],
                                                                                     python_short_ver))
        self.updatecfg('configopts', " -DPYTHON_LIBRARY=%s/lib/libpython%s.so" % (depsdict['Python'],
                                                                                  python_short_ver))

        # SuiteSparse config params
        suitesparse = depsdict['SuiteSparse']
        umfpack_params = ' -DUMFPACK_DIR="%s/UMFPACK"' % suitesparse
        umfpack_params += ' -DAMD_DIR="%s/UMFPACK"' % suitesparse
        umfpack_params += ' -DCHOLMOD_DIR="%s/CHOLMOD"' % suitesparse
        umfpack_params += ' -DUFCONFIG_DIR="%s/UFconfig"' % suitesparse
        umfpack_params += ' -DCAMD_LIBRARY:PATH="%s/CAMD/lib/libcamd.a"' % suitesparse
        umfpack_params += ' -DCCOLAMD_LIBRARY:PATH="%s/CCOLAMD/lib/libccolamd.a"' % suitesparse
        umfpack_params += ' -DCOLAMD_LIBRARY:PATH="%s/COLAMD/lib/libcolamd.a"' % suitesparse
        self.updatecfg('configopts', umfpack_params)

        # ParMETIS and SCOTCH
        self.updatecfg('configopts', ' -DPARMETIS_DIR="%s"' % depsdict['ParMETIS'])
        self.updatecfg('configopts', ' -DSCOTCH_DIR="%s" -DSCOTCH_DEBUG:BOOL=ON' % depsdict['SCOTCH'])

        # BLACS and LAPACK 
        self.updatecfg('configopts', ' -DBLAS_LIBRARIES:PATH="$LIBBLAS"')
        self.updatecfg('configopts', ' -DLAPACK_LIBRARIES:PATH="$LIBLAPACK"')

        # CGAL
        self.updatecfg('configopts', ' -DCGAL_DIR:PATH="$SOFTROOTCGAL"')

        # set correct openmp options
        openmp = self.tk.get_openmp_flag()
        self.updatecfg('configopts', ' -DOpenMP_CXX_FLAGS="%s"' % openmp)
        self.updatecfg('configopts', ' -DOpenMP_C_FLAGS="%s"' % openmp)

        # configure
        CMakePythonPackage.configure(self)

    def make_module_extra(self):
        """Set extra environment variables for Dolfin."""

        txt = CMakePythonPackage.make_module_extra(self)

        # Dolfin needs to find Boost and the UFC pkgconfig file
        txt += "setenv\tBOOST_DIR\t%s\n" % get_software_root('Boost')
        txt += "prepend-path\tPKG_CONFIG_PATH\t%s/lib/pkgconfig\n" % get_software_root('UFC')
        txt += "prepend-path\tPKG_CONFIG_PATH\t%s/lib/pkgconfig\n" % self.installdir

        envvars = ['I_MPI_CXX', 'I_MPI_CC']
        for envvar in envvars:
            envar_val = os.getenv(envvar)
            # if environment variable is set, also set it in module
            if envar_val:
                txt += "setenv\t%s\t%s\n" % (envvar, envar_val)

        return txt

    def sanitycheck(self):
        """Custom sanity check for Dolfin."""

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths', {'files': ['bin/dolfin-%s' % x for x in ['version', 'convert',
                                                                                     'order', 'plot']]
                                                    + ['include/dolfin.h'],
                                             'dirs':['%s/dolfin' % self.pylibdir]
                                            })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        CMakePythonPackage.sanitycheck(self)
