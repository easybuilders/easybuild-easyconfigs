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
from distutils.version import LooseVersion
import copy
import os

from easybuild.tools.build_log import getLog
from easybuild.tools.modules import Modules, get_software_root
from easybuild.tools import systemtools

import easybuild.tools.environment as env

# constant used for recognizing compilers, MPI libraries, ...
GCC = "GCC"
INTEL = "Intel"
OPENMPI = "OpenMPI"
QLOGIC = "QLogic"

class Toolkit:
    """
    Class for compiler toolkits, consisting out of a compiler and dependencies (libraries).
    """

    def __init__(self, name, version):
        """ Initialise toolkit variables."""

        self.dependencies = []
        self.vars = {}
        self.arch = None
        self.toolkit_deps = []
        self.m32flag = ''

        # logger
        self.log = getLog('Toolkit')

        # option flags
        self.opts = {
           'usempi': False, 'cciscxx': False, 'pic': False, 'opt': False,
           'noopt': False, 'lowopt': False, 'debug': False, 'optarch':True,
           'i8': False, 'unroll': False, 'verbose': False, 'cstd': None,
           'shared': False, 'static': False, 'intel-static': False,
           'loop': False, 'f2c': False, 'no-icc': False,
           'packed-groups': False, '32bit' : False
        }

        self.name = name
        self.version = version

        # 32-bit toolkit have version that ends with '32bit'
        if self.version.endswith('32bit'):
            self.opts['32bit'] = True
            self.m32flag = " -m32"

    def _toolkitExists(self, name=None, version=None):
        """
        Verify if there exists a toolkit by this name and version
        """
        if not name:
            name = self.name
        if not version:
            version = self.version

        if self.name == 'dummy':
            return True

        return Modules().exists(name, version)

    def setOptions(self, options):
        """ Process toolkit options """
        for opt in options.keys():
            ## Only process supported opts
            if opt in self.opts:
                self.opts[opt] = options[opt]
            else:
                self.log.warning("Undefined toolkit option %s specified." % opt)

    def getDependencyVersion(self, dependency):
        """ Generate a version string for a dependency on a module using this toolkit """
        # Add toolkit to version string
        toolkit = ''
        if self.name != 'dummy':
            toolkit = '-%s-%s' % (self.name, self.version)
        elif self.version != 'dummy':
            toolkit = '%s' % (self.version)

        # Check if dependency is independent of toolkit
        if 'dummy' in dependency and dependency['dummy']:
            toolkit = ''

        suffix = dependency.get('suffix', '')

        if 'version' in dependency:
            return "%s%s%s" % (dependency['version'], toolkit, suffix)
        else:
            matches = Modules().available(dependency['name'], "%s%s" % (toolkit, suffix))
            # Find the most recent (or default) one
            if len(matches) > 0:
                return matches[-1]
            else:
                self.log.error('No toolkit version for dependency name %s (suffix %s) found'
                           % (dependency['name'], "%s%s" % (toolkit, suffix)))

    def addDependencies(self, dependencies):
        """ Verify if the given dependencies exist and add them """
        mod = Modules()
        self.log.debug("Adding toolkit dependencies")
        for dep in dependencies:
            if not 'tk' in dep:
                dep['tk'] = self.getDependencyVersion(dep)

            if not mod.exists(dep['name'], dep['tk']):
                self.log.error('No module found for dependency %s/%s' % (dep['name'], dep['tk']))
            else:
                self.dependencies.append(dep)
                self.log.debug('Added toolkit dependency %s' % dep)

    def prepare(self, onlymod=None):
        """
        Prepare a set of environment parameters based on name/version of toolkit
        - load modules for toolkit and dependencies
        - generate extra variables and set them in the environment

        onlymod: Boolean/string to indicate if the toolkit should only load the enviornment
        with module (True) or also set all other variables (False) like compiler CC etc
        (If string: comma separated list of variables that will be ignored).
        """
        if not self._toolkitExists():
            self.log.error("No module found for toolkit name '%s' (%s)" % (self.name, self.version))

        if self.name == 'dummy':
            if self.version == 'dummy':
                self.log.info('Toolkit: dummy mode')
            else:
                self.log.info('Toolkit: dummy mode, but loading dependencies')
                modules = Modules()
                modules.addModule(self.dependencies)
                modules.load()
            return

        ## Load the toolkit and dependencies modules
        modules = Modules()
        modules.addModule([(self.name, self.version)])
        modules.addModule(self.dependencies)
        modules.load()

        ## Determine direct toolkit dependencies, so we can prepare for them
        self.toolkit_deps = modules.dependencies_for(self.name, self.version, depth=1)
        self.log.debug('List of direct toolkit dependencies: %s' % self.toolkit_deps)

        ## Generate the variables to be set
        self._generate_variables()

        ## set the variables
        if not (onlymod == True):
            self.log.debug("Variables being set: onlymod=%s" % onlymod)

            ## add LDFLAGS and CPPFLAGS from dependencies to self.vars
            self._addDependencyVariables()
            self._setVariables(onlymod)
        else:
            self.log.debug("No variables set: onlymod=%s" % onlymod)

    def _addDependencyVariables(self, names=None):
        """ Add LDFLAGS and CPPFLAGS to the self.vars based on the dependencies
        names should be a list of strings containing the name of the dependency"""
        cpp_paths = ['include']
        ld_paths = ['lib64', 'lib']

        if not names:
            deps = self.dependencies
        else:
            deps = [{'name':name} for name in names]

        for dep in deps:
            softwareRoot = get_software_root(dep['name'])
            if not softwareRoot:
                self.log.error("%s was not found in environment (dep: %s)" % (dep['name'], dep))

            self._flagsForSubdirs(softwareRoot, cpp_paths, flag="-I%s", varskey="CPPFLAGS")
            self._flagsForSubdirs(softwareRoot, ld_paths, flag="-L%s", varskey="LDFLAGS")

    def _setVariables(self, dontset=None):
        """ Sets the environment variables """
        self.log.debug("Setting variables: dontset=%s" % dontset)

        dontsetlist = []
        if type(dontset) == str:
            dontsetlist = dontset.split(',')
        elif type(dontset) == list:
            dontsetlist = dontset

        for key, val in self.vars.items():
            if key in dontsetlist:
                self.log.debug("Not setting environment variable %s (value: %s)." % (key, val))
                continue

            self.log.debug("Setting environment variable %s to %s" % (key, val))
            env.set(key, val)

            # also set unique named variables that can be used in Makefiles
            # - so you can have 'CFLAGS = $(SOFTVARCFLAGS)'
            # -- 'CLFLAGS = $(CFLAGS)' gives  '*** Recursive variable `CFLAGS'
            # references itself (eventually).  Stop' error
            env.set("SOFTVAR%s" % key, val)


    def _getOptimalArchitecture(self):
        """ Get options for the current architecture """
        optarchs = {systemtools.INTEL : 'xHOST', systemtools.AMD : 'msse3'}
        if not self.arch:
            self.arch = systemtools.get_cpu_vendor()
        if self.arch in optarchs:
            optarch = optarchs[self.arch]
            self.log.info("Using %s as optarch for %s." % (optarch, self.arch))
            return optarch
        else:
            self.log.error("Don't know how to set optarch for %s." % self.arch)

    def _generate_variables(self):

        # list of preparation function
        # number are assigned to indicate order in which they need to be run
        known_preparation_functions = {
            # compilers always go first
            '1_GCC':self.prepareGCC,
            '1_icc':self.prepareIcc,
            '1_ifort':self.prepareIfort,
            # MPI libraries
            '2_impi':self.prepareIMPI,
            '2_MPICH2':self.prepareMPICH2,
            '2_MVAPICH2':self.prepareMVAPICH2,
            '2_OpenMPI':self.prepareOpenMPI,
            '2_QLogicMPI':self.prepareQLogicMPI,
            # BLAS libraries, LAPACK, FFTW
            '3_ATLAS':self.prepareATLAS,
            '3_FFTW':self.prepareFFTW,
            '3_GotoBLAS':self.prepareGotoBLAS,
            '3_imkl':self.prepareIMKL,
            '3_ACML': self.prepareACML,
            '4_LAPACK':self.prepareLAPACK,
            # BLACS, FLAME, ScaLAPACK, ...
            '5_BLACS':self.prepareBLACS,
            '5_FLAME':self.prepareFLAME,
            '6_ScaLAPACK':self.prepareScaLAPACK,
            # other stuff
            '7_itac':self.prepareItac
        }

        # sort to ensure correct order
        meth_keys = known_preparation_functions.keys()
        meth_keys.sort()

        # obtain list of dependency names
        depnames = []
        for dep in self.toolkit_deps:
            depnames.append(dep['name'])
        ## if toolkit name has a preparation function, add it as well
        for meth_key in meth_keys:
            if meth_key.endswith("_%s" % self.name):
                depnames.append(self.name)
                self.log.debug("Going to add preparation function for toolkit %s itself also" % self.name)
                break
        self.log.debug("depnames: %s" % depnames)

        # figure out which preparation functions we need to run based on toolkit dependencies
        preparation_functions = {}
        for meth in meth_keys:
            for dep in depnames:
                # bit before first '_' is used for ordering
                meth_name = '_'.join(meth.split('_')[1:])
                if dep.lower() == meth_name.lower():
                    preparation_functions.update({meth:known_preparation_functions[meth]})
                    break

        if not len(depnames) == len(preparation_functions.values()):
            found_meths = ['_'.join(meth.split('_')[1:]) for meth in preparation_functions.keys()]
            for depname in copy.copy(depnames):
                if depname in found_meths:
                    depnames.remove(depname)
            self.log.error("Unable to find preparation functions for these toolkit dependencies: %s" % depnames)

        self.log.debug("List of preparation functions: %s" % preparation_functions)

        self.vars["LDFLAGS"] = ''
        self.vars["CPPFLAGS"] = ''
        self.vars['LIBS'] = ''

        # run preparation functions, in order as determined by keys
        for key in sorted(preparation_functions.keys()):
            preparation_functions[key]()

    def prepareACML(self):
        """
        Prepare for AMD Math Core Library (ACML)
        """

        if self.opts['32bit']:
            self.log.error("ERROR: 32-bit not supported (yet) for ACML.")

        self._addDependencyVariables(['ACML'])

        if self.toolkit_comp_family() == GCC:
            compiler = 'gfortran'
        elif self.toolkit_comp_family() == INTEL:
            compiler = 'ifort'
        else:
            self.log.error("Don't know which compiler-specific subdir for ACML to use.")
        self.vars['LDFLAGS'] += " -L%(acml)s/%(comp)s64/lib/ " % {
        #                       "%(acml)s/%(comp)s64/lib/libacml.a -lpthread" % {
                                                'comp':compiler,
                                                'acml':os.environ['SOFTROOTACML']
               }
        self.vars['LIBBLAS'] = " -lacml_mv -lacml " #-lpthread"

        self.vars['LIBBLAS_MT'] = self.vars['LIBBLAS']

        self.vars['LIBLAPACK'] = self.vars['LIBBLAS']
        self.vars['LIBLAPACK_MT'] = self.vars['LIBBLAS_MT']

    def prepareATLAS(self):
        """
        Prepare for ATLAS BLAS/LAPACK library
        """

        self.vars['LIBBLAS'] = " -lcblas -lf77blas -latlas -lgfortran"
        self.vars['LIBBLAS_MT'] = " -lptcblas -lptf77blas -latlas -lgfortran -lpthread"

        self._addDependencyVariables(['ATLAS'])

    def prepareBLACS(self):
        """
        Prepare for BLACS library
        """

        self.vars['LIBSCALAPACK'] = " -lblacsF77init -lblacs "
        self.vars['LIBSCALAPACK_MT'] = self.vars['LIBSCALAPACK']

        self._addDependencyVariables(['BLACS'])

    def prepareFLAME(self):
        """
        Prepare for FLAME library
        """

        self.vars['LIBLAPACK'] += " -llapack2flame -lflame "
        self.vars['LIBLAPACK_MT'] += " -llapack2flame -lflame "

        self._addDependencyVariables(['FLAME'])

    def prepareFFTW(self):
        """
        Prepare for FFTW library
        """

        suffix = ''
        if os.getenv('SOFTVERSIONFFTW').startswith('3.'):
            suffix = '3'
        self.vars['LIBFFT'] = " -lfftw%s " % suffix
        if self.opts['usempi']:
            self.vars['LIBFFT'] += " -lfftw%s_mpi " % suffix

        self._addDependencyVariables(['FFTW'])

    def prepareGCC(self, withMPI=True):
        """
        Prepare for a GCC-based compiler toolkit
        """

        if self.opts['32bit']:
            self.log.error("ERROR: 32-bit not supported yet for GCC based toolkits.")

        # set basic GCC options
        self.vars['CC'] = 'gcc %s' % self.m32flag
        self.vars['CXX'] = 'g++ %s' % self.m32flag
        self.vars['F77'] = 'gfortran %s ' % self.m32flag
        self.vars['F90'] = 'gfortran %s' % self.m32flag

        if self.opts['cciscxx']:
            self.vars['CXX'] = self.vars['CC']

        flags = []

        if self.opts['optarch']:
            ## difficult for GCC
            flags.append("march=native")

        flags.append(self._getOptimizationLevel())
        flags.extend(self._flagsForOptions(override={
            'i8': 'fdefault-integer-8',
            'unroll': 'funroll-loops',
            'f2c': 'ff2c',
            'loop': ['ftree-switch-conversion', 'floop-interchange',
                     'floop-strip-mine', 'floop-block']
        }))

        copts = []
        if self.opts['cstd']:
            copts.append("std=%s" % self.opts['cstd'])

        if len(flags + copts) > 0:
            self.vars['CFLAGS'] = "%s" % ('-' + ' -'.join(flags + copts))
        if len(flags) > 0:
            self.vars['CXXFLAGS'] = "%s" % ('-' + ' -'.join(flags))
        if len(flags) > 0:
            self.vars['FFLAGS'] = "%s" % ('-' + ' -'.join(flags))
        if len(flags) > 0:
            self.vars['F90FLAGS'] = "%s" % ('-' + ' -'.join(flags))

        ## to get rid of lots of problems with libgfortranbegin
        ## or remove the system gcc-gfortran
        self.vars['FLIBS'] = "-lgfortran"

    def prepareGotoBLAS(self):
        """
        Prepare for GotoBLAS BLAS library
        """

        self.vars['LIBBLAS'] = "-lgoto"
        self.vars['LIBBLAS_MT'] = self.vars['LIBBLAS']

        self._addDependencyVariables(['GotoBLAS'])

    def prepareIntelCompiler(self, name):

        version = os.getenv('SOFTVERSION%s' % name.upper())
        root = os.getenv('SOFTROOT%s' % name.upper())

        if "liomp5" not in self.vars['LIBS']:
            if LooseVersion(version) < LooseVersion('2011'):
                self.vars['LIBS'] += " -liomp5 -lguide -lpthread"
            else:
                self.vars['LIBS'] += " -liomp5 -lpthread"

        if LooseVersion(version) < LooseVersion('2011.4'):
            libs = ['lib/intel64', 'lib/ia32']
        else:
            libs = ['compiler/lib/intel64', 'compiler/lib/ia32']
        self._flagsForSubdirs(root, libs, flag="-L%s", varskey="LDFLAGS")

    def prepareIcc(self):
        """
        Prepare for an icc based compiler toolkit
        """

        self.vars['CC'] = 'icc%s' % self.m32flag
        self.vars['CXX'] = 'icpc%s' % self.m32flag

        if self.opts['cciscxx']:
            self.vars['CXX'] = self.vars['CC']

        flags = []
        if self.opts['optarch']:
            flags.append(self._getOptimalArchitecture())

        flags.append(self._getOptimizationLevel())
        flags.extend(self._flagsForOptions(override={
            'intel-static': 'static-intel',
            'no-icc': 'no-icc'
        }))

        copts = []
        if self.opts['cstd']:
            copts.append("std=%s" % self.opts['cstd'])

        if len(flags + copts) > 0:
            self.vars['CFLAGS'] = '-' + ' -'.join(flags + copts)
        if len(flags) > 0:
            self.vars['CXXFLAGS'] = '-' + ' -'.join(flags)

        self.prepareIntelCompiler('icc')

    def prepareIfort(self):
        """
        Prepare for an ifort based compiler toolkit
        """

        self.vars['F77'] = 'ifort%s' % self.m32flag
        self.vars['F90'] = 'ifort%s' % self.m32flag

        flags = []
        if self.opts['optarch']:
            flags.append(self._getOptimalArchitecture())

        flags.append(self._getOptimizationLevel())
        flags.extend(self._flagsForOptions(override={
            'intel-static': 'static-intel'
        }))

        if len(flags) > 0:
            self.vars['FFLAGS'] = '-' + ' -'.join(flags)

        self.prepareIntelCompiler('ifort')

    def prepareIMKL(self):
        """
        Prepare toolkit for IMKL: Intel Math Kernel Library
        """

        mklRoot = os.getenv('MKLROOT')
        if not mklRoot:
            self.log.error("MKLROOT not found in environment")

        # For more inspiration: see http://software.intel.com/en-us/articles/intel-mkl-link-line-advisor/

        libsfx = "_lp64"
        libsfxsl = "_lp64"
        if self.opts['32bit']:
            libsfx = ""
            libsfxsl = "_core"

        self.vars['LIBLAPACK'] = "-Wl:-Bstatic -Wl,--start-group -lmkl_intel%s -lmkl_sequential " \
                                 "-lmkl_core -Wl,--end-group -Wl:-Bdynamic" % libsfx
        self.vars['LIBBLAS'] = self.vars['LIBLAPACK']

        self.vars['LIBLAPACK_MT'] = "-Wl:-Bstatic -Wl,--start-group -lmkl_intel%s -lmkl_intel_thread " \
                                    "-lmkl_core -Wl,--end-group -Wl:-Bdynamic -liomp5 -lpthread" % libsfx
        self.vars['LIBBLAS_MT'] = self.vars['LIBLAPACK_MT']

        self.vars['LIBSCALAPACK'] = "-Wl:-Bstatic -lmkl_scalapack%(libsfxsl)s " \
                                    "-lmkl_solver%(libsfx)s_sequential " \
                                    "-Wl,--start-group -lmkl_intel%(libsfx)s " \
                                    "-lmkl_sequential -lmkl_core -lmkl_blacs_intelmpi%(libsfx)s " \
                                    "-Wl,--end-group -Wl:-Bdynamic" % {
                                                                       'libsfx':libsfx,
                                                                       'libsfxsl':libsfxsl
                                                                       }

        fftwsuff=""
        if self.opts['pic']:
            fftwsuff="_pic"
        # only include interface lib if it's there
        fftlib = "-Wl:-Bstatic -lfftw3xc_intel%s -Wl:-Bdynamic" % fftwsuff

        self.vars['LIBFFT'] = ''
        if os.path.exists(fftlib):
            self.vars['LIBFFT'] += fftlib

        if self.opts['packed-groups']: #we pack groups toghether, since some tools like pkg-utils don't work well with them
            for i in ['LIBLAPACK', 'LIBBLAS', 'LIBLAPACK_MT', 'LIBSCALAPACK' ]:
                self.vars[i] = self.vars[i].replace(" ", ",").replace("-Wl,--end-group", "--end-group")

        lib = self.vars['LIBSCALAPACK']
        lib = lib.replace('mkl_solver%s_sequential' % libsfx, 'mkl_solver')
        lib = lib.replace('mkl_sequential', 'mkl_intel_thread') + ' -liomp5 -lpthread'
        self.vars['LIBSCALAPACK_MT'] = lib

        # Exact paths/linking statements depend on imkl version
        if LooseVersion(os.environ['SOFTVERSIONIMKL']) < LooseVersion('10.3'):
            if self.opts['32bit']:
                mklld = ['lib/32']
            else:
                mklld = ['lib/em64t']
            mklcpp = ['include', 'include/fftw']
        else:
            if self.opts['32bit']:
                self.log.error("32-bit libraries not supported yet for IMKL v%s (> v10.3)" % os.environ("SOFTROOTIMKL"))

            mklld = ['lib/intel64', 'mkl/lib/intel64']
            mklcpp = ['mkl/include', 'mkl/include/fftw']

        # Linker flags
        self._flagsForSubdirs(mklRoot, mklld, flag="-L%s", varskey="LDFLAGS")
        self._flagsForSubdirs(mklRoot, mklcpp, flag="-I%s", varskey="CPPFLAGS")

        if self.toolkit_comp_family() == GCC:
            for var in ['LIBLAPACK', 'LIBLAPACK_MT', 'LIBSCALAPACK', 'LIBSCALAPACK_MT']:
                self.vars[var] = self.vars[var].replace('mkl_intel_lp64', 'mkl_gf_lp64')

    def prepareIMPI(self):
        """
        Prepare for Intel MPI library
        """

        if self.toolkit_comp_family() == INTEL:
            # Intel-based toolkit

            self.vars['MPICC'] = 'mpiicc %s' % self.m32flag
            self.vars['MPICXX'] = 'mpiicpc %s' % self.m32flag
            self.vars['MPIF77'] = 'mpiifort %s' % self.m32flag
            self.vars['MPIF90'] = 'mpiifort %s' % self.m32flag

            if self.opts['usempi']:
                for i in ['CC', 'CXX', 'F77', 'F90']:
                    self.vars[i] = self.vars["MPI%s" % i]

            # used by mpicc and mpicxx to actually use mpiicc and mpiicpc
            self.vars['I_MPI_CXX'] = "icpc"
            self.vars['I_MPI_CC'] = "icc"

            if self.opts['cciscxx']:
                self.vars['MPICXX'] = self.vars['MPICC']

        else:
            # other compilers (e.g. GCC) with Intel MPI
            self.vars['MPICC'] = 'mpicc -cc=%s %s ' % (self.vars['CC'], self.m32flag)
            self.vars['MPICXX'] = 'mpicxx -cxx=%s %s ' % (self.vars['CXX'], self.m32flag)
            self.vars['MPIF77'] = 'mpif77 -fc=%s %s ' % (self.vars['F77'], self.m32flag)
            self.vars['MPIF90'] = 'mpif90 -fc=%s %s ' % (self.vars['F90'], self.m32flag)

    def prepareItac(self):
        """
        Prepare for Intel Trace Collector library
        """
        pass

    def prepareQLogicMPI(self):

        ## QLogic specific
        self.vars['MPICC'] = 'mpicc -cc="%s"' % self.vars['CC']
        self.vars['MPICXX'] = 'mpicxx -CC="%s"' % self.vars['CXX']
        self.vars['MPIF77'] = 'mpif77 -fc="%s"' % self.vars['F77']
        self.vars['MPIF90'] = 'mpif90 -f90="%s"' % self.vars['F90']

        if self.opts['usempi']:
            for i in ['CC', 'CXX', 'F77', 'F90']:
                self.vars[i] = self.vars["MPI%s" % i]

    def prepareLAPACK(self):
        """
        Prepare for LAPACK library
        """

        self.vars['LIBLAPACK'] = "-llapack %s" % self.vars['LIBBLAS']
        self.vars['LIBLAPACK_MT'] = "-llapack %s -lpthread" % self.vars['LIBBLAS_MT']

        self._addDependencyVariables(['LAPACK'])

    def prepareMPICH2(self):
        """
        Prepare for MPICH2 MPI library (e.g. ScaleMP's version)
        """
        if "vSMP" in os.getenv('SOFTVERSIONMPICH2'):
            # ScaleMP MPICH specific
            self.vars['MPICC'] = 'mpicc -cc="%s %s"' % (self.vars['CC'], self.m32flag)
            self.vars['MPICXX'] = 'mpicxx -CC="%s %s"' % (self.vars['CXX'], self.m32flag)
            self.vars['MPIF77'] = 'mpif77 -fc="%s %s"' % (self.vars['F77'], self.m32flag)
            self.vars['MPIF90'] = 'mpif90 -f90="%s %s"' % (self.vars['F90'], self.m32flag)

            if self.opts['cciscxx']:
                self.vars['MPICXX'] = self.vars['MPICC']

            if self.opts['usempi']:
                for i in ['CC', 'CXX', 'F77', 'F90']:
                    self.vars[i] = self.vars["MPI%s" % i]
        else:
            self.log.error("Don't know how to prepare for a non-ScaleMP MPICH2 library.")

    def prepareSimpleMPI(self):
        """
        Prepare for 'simple' MPI libraries (e.g. MVAPICH2, OpenMPI)
        """

        self.vars['MPICC'] = 'mpicc %s' % self.m32flag
        self.vars['MPICXX'] = 'mpicxx %s' % self.m32flag
        self.vars['MPIF77'] = 'mpif77 %s' % self.m32flag
        self.vars['MPIF90'] = 'mpif90 %s' % self.m32flag

        if self.opts['cciscxx']:
            self.vars['MPICXX'] = self.vars['MPICC']

        if self.opts['usempi']:
            for i in ['CC', 'CXX', 'F77', 'F90']:
                self.vars[i] = self.vars["MPI%s" % i]

    def prepareMVAPICH2(self):
        """
        Prepare for MVAPICH2 MPI library
        """
        self.prepareSimpleMPI()

    def prepareOpenMPI(self):
        """
        Prepare for OpenMPI MPI library
        """
        self.prepareSimpleMPI()

    def prepareScaLAPACK(self):
        """
        Prepare for ScaLAPACK library
        """

        # we need to be careful here, LIBSCALAPACK(_MT) may be set by prepareBLACS, or not
        self.vars['LIBSCALAPACK'] = "%s -lscalapack" % self.vars.get('LIBSCALAPACK', '')
        self.vars['LIBSCALAPACK_MT'] = "%s %s -lpthread" % (self.vars['LIBSCALAPACK'],
                                                            self.vars.get('LIBSCALAPACK_MT', ''))

        self._addDependencyVariables(['ScaLAPACK'])

    def _getOptimizationLevel(self):
        """ Default is 02, but set it explicitly (eg -g otherwise becomes -g -O0)"""
        if self.opts['noopt']:
            return 'O0'
        elif self.opts['opt']:
            return 'O3'
        elif self.opts['lowopt']:
            return 'O1'
        else:
            return 'O2'

    def _flagsForOptions(self, override=None):
        """
        Parse options to flags.
        """
        flags = []

        flagOptions = {
            'pic': 'fPIC', 'debug': 'g', 'i8': 'i8',
            'static': 'static', 'unroll': 'unroll', 'verbose': 'v', 'shared': 'shared',
        }
        if override:
            flagOptions.update(override)

        for key in flagOptions.keys():
            if self.opts[key]:
                newFlags = flagOptions[key]
                if type(newFlags) == list:
                    flags.extend(newFlags)
                else:
                    flags.append(newFlags)

        return flags

    def _flagsForSubdirs(self, base, subdirs, flag="-L%s", varskey=None):
        """ Generate include flags to pass to the compiler """
        flags = []
        for subdir in subdirs:
            directory = os.path.join(base, subdir)
            if os.path.isdir(directory):
                flags.append(flag % directory)
            else:
                self.log.warning("Directory %s was not found" % directory)

        if not varskey in self.vars:
            self.vars[varskey] = ''
        self.vars[varskey] += ' ' + ' '.join(flags)

    def det_toolkit_type(self, name, type_map):
        """Determine type of toolkit based on toolkit dependencies."""

        toolkit_dep_names = [dep['name'] for dep in self.toolkit_deps]

        for req_mods, tk_type in type_map.items():
            match = True
            for req_mod in req_mods:
                if not req_mod in toolkit_dep_names:
                    match = False
            if match:
                return tk_type

        self.log.error("Failed to determine %s based on toolkit dependencies." % name)

    def toolkit_comp_family(self):
        """Determine compiler family based on toolkit dependencies."""
        comp_families = {
                         # always use tuples as keys!
                         ('icc', 'ifort'):INTEL, # Intel toolkit has both icc and ifort
                         ('GCC', ):GCC # GCC toolkit uses GCC as compiler suite
                         }

        return self.det_toolkit_type("compiler family", comp_families)

    def get_openmp_flag(self):
        """Determine compiler flag for OpenMP"""

        if self.toolkit_comp_family() == INTEL:
            return "-openmp"
        elif self.toolkit_comp_family() == GCC:
            return "-fopenmp"
        else:
            self.log.error("Can't determine compiler flag for OpenMP.")

    def toolkit_mpi_type(self):
        """Determine type of MPI library based on toolkit dependencies."""
        mpi_types = {
                      # always use tuples as keys!
                      ('impi', ):INTEL, # Intel MPI
                      ('OpenMPI', ):OPENMPI, # OpenMPI
                      ('QLogicMPI', ):QLOGIC # QLogic MPI
                      }

        return self.det_toolkit_type("type of mpi library", mpi_types)

    def mpi_cmd_for(self, cmd, nr_ranks):
        """Construct an MPI command for the given command and number of ranks."""

        # parameter values for mpirun command
        params = {'nr_ranks':nr_ranks, 'cmd':cmd}

        # different known mpirun commands
        mpi_cmds = {
                    OPENMPI:"mpirun -n %(nr_ranks)d %(cmd)s",
                    INTEL:"mpirun %(mpdbootfile)s %(nodesfile)s -np %(nr_ranks)d %(cmd)s",
                    }

        mpi_type = self.toolkit_mpi_type()

        # Intel MPI mpirun needs more work
        if mpi_type == INTEL:

            # set temporary dir for mdp
            env.set('I_MPI_MPD_TMPDIR', "/tmp")

            # set PBS_ENVIRONMENT, so that --file option for mpdboot isn't stripped away
            env.set('PBS_ENVIRONMENT', "PBS_BATCH_MPI")

            # create mpdboot file
            fn = "/tmp/mpdboot"
            try:
                if os.path.exists(fn):
                    os.remove(fn)
                f = open(fn, "w")
                f.write("localhost ifhn=localhost")
                f.close()
            except (OSError, IOError), err:
                self.log.error("Failed to create file %s: %s" % (fn, err))

            params.update({'mpdbootfile':"--file=%s"%fn})

            # create nodes file
            fn = "/tmp/nodes"
            try:
                if os.path.exists(fn):
                    os.remove(fn)
                f = open(fn, "w")
                f.write("localhost\n" * nr_ranks)
                f.close()
            except (OSError, IOError), err:
                self.log.error("Failed to create file %s: %s" % (fn, err))

            params.update({'nodesfile':"-machinefile %s"%fn})

        if mpi_type in mpi_cmds.keys():
            return mpi_cmds[mpi_type] % params
        else:
            self.log.error("Don't know how to create an MPI command for MPI library of type '%s'." % mpi_type)
