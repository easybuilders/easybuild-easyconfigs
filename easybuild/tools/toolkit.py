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
import os
import re

from easybuild.tools.build_log import getLog
from easybuild.tools.modules import Modules, getSoftwareRoot

log = getLog('Toolkit')

class Toolkit:
    """
    Class for compiler toolkits, consisting out of a compiler and dependencies (libraries).
    """

    def __init__(self, name, version):
        """ Initialise toolkit name version """
        self.dependencies = []
        self.vars = {}
        self.arch = None

        ## Option flags
        self.opts = {
           'usempi': False, 'cciscxx': False, 'pic': False, 'opt': False,
           'noopt': False, 'lowopt': False, 'debug': False, 'optarch':True,
           'i8': False, 'unroll': False, 'verbose': False, 'cstd': None,
           'shared': False, 'static': False, 'intel-static': False,
           'loop': False, 'f2c': False, 'no-icc': False,
        }

        self.name = name
        self.version = version

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
                log.warning("Undefined toolkit option %s specified." % opt)

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
                log.error('No toolkit version for dependency name %s (suffix %s) found'
                           % (dependency['name'], "%s%s" % (toolkit, suffix)))

    def addDependency(self, dependencies):
        """ Verify if the given dependencies exist and add them """
        mod = Modules()
        for dep in dependencies:
            if not 'tk' in dep:
                dep['tk'] = self.getDependencyVersion(dep)

            if not mod.exists(dep['name'], dep['tk']):
                log.error('No module found for dependency %s/%s' % (dep['name'], dep['tk']))
            else:
                self.dependencies += [dep]

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
            log.error("No module found for toolkit name '%s' (%s)" % (self.name, self.version))

        if self.name == 'dummy':
            if self.version == 'dummy':
                log.info('Toolkit: dummy mode')
            else:
                log.info('Toolkit: dummy mode, but loading dependencies')
                modules = Modules()
                modules.addModule(self.dependencies)
                modules.load()
            return

        ## Load the toolkit module
        modules = Modules()
        modules.addModule([[self.name, self.version]])
        modules.addModule(self.dependencies)
        modules.load()

        self._determineArchitecture()

        ## Generate the variables to be set
        preparationMethods = {
            'GCC': self.prepareGCC,
            'gimkl': self.prepareGimkl,
            'gmgfl': self.prepareG_gfl,
            'gogfl': self.prepareG_gfl,
            'gqacml': self.prepareG_acml,
            'gmqacml': self.prepareG_acml,
            'icc': self.prepareIccBased,
            'ictce': self.prepareIctce,
            'iqacml': self.prepareIqacml,
            'ismkl': self.prepareIsmkl,
        }

        if self.name in preparationMethods:
            m32 = False
            if self.version.endswith("32bit"):
                m32 = True
            preparationMethods[self.name](m32=m32)
        else:
            log.error("Don't know how to prepare toolkit '%s'." % self.name)

        ## set the variables
        if not (onlymod == True):
            log.debug("Variables being set: onlymod=%s" % onlymod)

            ## add LDFLAGS and CPPFLAGS from dependencies to self.vars
            self._addDependencyVariables()
            self._setVariables(onlymod)
        else:
            log.debug("No variables set: onlymod=%s" % onlymod)

    def _addDependencyVariables(self, deps=None):
        """ Add LDFLAGS and CPPFLAGS to the self.vars based on the dependencies """
        cpp_paths = ['include']
        ld_paths = ['lib64', 'lib']

        if not deps:
            deps = self.dependencies

        for dep in deps:
            softwareRoot = getSoftwareRoot(dep['name'])
            if not softwareRoot:
                log.error("%s was not found in environment (dep: %s)" % (dep['name'], dep))

            self._flagsForSubdirs(softwareRoot, cpp_paths, flag="-I%s", varskey="CPPFLAGS")
            self._flagsForSubdirs(softwareRoot, ld_paths, flag="-L%s", varskey="LDFLAGS")

    def _setVariables(self, dontset=None):
        """ Sets the environment variables """
        log.debug("Setting variables: dontset=%s" % dontset)

        dontsetlist = []
        if type(dontset) == str:
            dontsetlist = dontset.split(',')
        elif type(dontset) == list:
            dontsetlist = dontset

        for key, val in self.vars.items():
            if key in dontsetlist:
                log.debug("Not setting environment variable %s (value: %s)." % (key, val))
                continue

            log.debug("Setting environment variable %s to %s" % (key, val))
            os.environ[key] = val

            # also set unique named variables that can be used in Makefiles
            # - so you can have 'CFLAGS = $(SOFTVARCFLAGS)'
            # -- 'CLFLAGS = $(CFLAGS)' gives  '*** Recursive variable `CFLAGS'
            # references itself (eventually).  Stop' error
            os.environ["SOFTVAR%s" % key] = val

    def _determineArchitecture(self):
        """ Determine the CPU architecture """
        regexp = re.compile(r"^vendor_id\s+:\s*(?P<vendorid>\S+)\s*$", re.M)
        arch = regexp.search(open("/proc/cpuinfo").read()).groupdict()['vendorid']

        archd = {'GenuineIntel': 'Intel', 'AuthenticAMD': 'AMD'}
        if arch in archd:
            self.arch = archd[arch]
        else:
            log.error("Unknown architecture detected: %s" % arch)

    def _getOptimalArchitecture(self):
        """ Get options for the current architecture """
        optarchs = {'Intel':'xHOST', 'AMD':'msse3'}

        if self.arch in optarchs:
            optarch = optarchs[self.arch]
            log.info("Using %s as optarch for %s." % (optarch, self.arch))
            return optarch
        else:
            log.error("Don't know how to set optarch for %s." % self.arch)

    def prepareGCCBased(self, withMPI=True, intelMPI=False, m32=False):

        if m32:
            log.error("ERROR: m32 not supported yet for GCC based toolkits.")

        # set basic GCC options
        self.vars['CC'] = 'gcc'
        self.vars['CXX'] = 'g++'
        self.vars['F77'] = 'gfortran'
        self.vars['F90'] = 'gfortran'

        if intelMPI:
            self.vars['MPICC'] = 'mpicc -cc=%s' % self.vars['CC']
            self.vars['MPICXX'] = 'mpicxx -cxx=%s' % self.vars['CXX']
            self.vars['MPIF77'] = 'mpif77 -fc=%s' % self.vars['F77']
            self.vars['MPIF90'] = 'mpif90 -fc=%s' % self.vars['F90']
        elif withMPI:
            self.vars['MPICC'] = 'mpicc'
            self.vars['MPICXX'] = 'mpicxx'
            self.vars['MPIF77'] = 'mpif77'
            self.vars['MPIF90'] = 'mpif90'

        if self.opts['usempi']:
            for i in ['CC', 'CXX', 'F77', 'F90']:
                self.vars[i] = self.vars["MPI%s" % i]

        if self.opts['cciscxx']:
            self.vars['CXX'] = self.vars['CC']
            if withMPI:
                self.vars['MPICXX'] = self.vars['MPICC']

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

        self.vars["LDFLAGS"] = ""
        self.vars["CPPFLAGS"] = ""
        self.vars['LIBS'] = ""
        self.vars['LIBSCALAPACK'] = "-lscalapack -lblacsF77init -lblacs"

        ## to get rid of lots of problems with libgfortranbegin
        ## or remove the system gcc-gfortran
        ##self.vars['FLIBS']="-lgfortran"

    def prepareGCC(self, m32=False):
        """ Prepare for gcc toolkit """
        self.prepareGCCBased(withMPI=False, m32=m32)

    def prepareG_gfl(self, m32=False):
        """ Prepare for g*gfl toolkit: GCC+LAPACK+GotoBLAS+FLAME and some MPI lib """
        self.prepareGCCBased(m32=m32)

        ## all is based on SOFTROOT environment variables
        ## MVAPICH2 is dealt with by mpi{cc,cxx,f77,f90}
        g_gfldeps = [{'name': 'GotoBLAS'}, {'name': 'FLAME'}, {'name': 'LAPACK'},
                     {'name': 'BLACS'}, {'name': 'ScaLAPACK'}]
        self._addDependencyVariables(g_gfldeps)

    def prepareGimkl(self, m32=False):
        """ Prepare for gimkl toolkit: GCC+IMPI+IMKL """
        self.prepareGCCBased(intelMPI=True, m32=m32)
        self.prepareIMKL(m32=m32)

        for var in ['LIBLAPACK', 'LIBLAPACK_MT', 'LIBSCALAPACK', 'LIBSCALAPACK_MT']:
            self.vars[var] = self.vars[var].replace('mkl_intel_lp64', 'mkl_gf_lp64')

    def prepareG_acml(self, m32=False):
        """ Prepare for g*acml toolkit: GCC+ACML and some MPI lib"""
        self.prepareGCCBased(m32=m32)
        self.prepareACML('gfortran', m32=m32)

    def prepareIccBased(self, withIMPI=False, m32=False):
        """ Set basic ICC info """
        mpiprefix = ''
        if self.opts['usempi'] and withIMPI:
            mpiprefix = 'mpi'

        m32flag = ""
        if m32:
            m32flag = " -m32"

        self.vars['CC'] = '%sicc%s' % (mpiprefix, m32flag)
        self.vars['CXX'] = '%sicpc%s' % (mpiprefix, m32flag)
        self.vars['F77'] = '%sifort%s' % (mpiprefix, m32flag)
        self.vars['F90'] = '%sifort%s' % (mpiprefix, m32flag)

        if withIMPI:
            self.vars['MPICC'] = 'mpiicc%s' % m32flag
            self.vars['MPICXX'] = 'mpiicpc%s' % m32flag
            self.vars['MPIF77'] = 'mpiifort%s' % m32flag
            self.vars['MPIF90'] = 'mpiifort%s' % m32flag

        if self.opts['cciscxx']:
            self.vars['CXX'] = self.vars['CC']
            if withIMPI:
                self.vars['MPICXX'] = self.vars['MPICC']

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
        if len(flags) > 0:
            self.vars['FFLAGS'] = '-' + ' -'.join(flags)

        self.vars['LDFLAGS'] = ''
        self.vars['CPPFLAGS'] = ''
        self.vars['LIBS'] = ''

    def prepareIctce(self, m32=False):
        """ Prepare for ictce toolkit """
        self.prepareIccBased(withIMPI=True, m32=m32)
        self.prepareIMKL(m32=m32)

        if LooseVersion(os.environ['SOFTVERSIONICC']) < LooseVersion('2011'):
            self.vars['LIBS'] += " -liomp5 -lguide -lpthread"
        else:
            self.vars['LIBS'] += " -liomp5 -lpthread"

    def prepareIqacml(self, m32=False):
        """ Prepare for iqacml toolkit: icc+qlogic mpi+acml """
        self.prepareIccBased(m32=m32)
        self.prepareACML('intel', m32=m32)

        ## QLogic specific
        self.vars['MPICC'] = 'mpicc -cc=icc'
        self.vars['MPICXX'] = 'mpicxx -CC=icpc'
        self.vars['MPIF77'] = 'mpif77 -fc=ifort'
        self.vars['MPIF90'] = 'mpif90 -f90=ifort'

    def prepareIsmkl(self, m32=False):
        """ Prepare for ismkl toolkit: icc+ScaleMP mpi+mkl """
        self.prepareIccBased(m32=m32)
        self.prepareIMKL(m32=m32)

        # ScaleMP MPICH specific
        self.vars['MPICC'] = 'mpicc -cc=icc'
        self.vars['MPICXX'] = 'mpicxx -CC=icpc'
        self.vars['MPIF77'] = 'mpif77 -fc=ifort'
        self.vars['MPIF90'] = 'mpif90 -f90=ifort'

    def prepareACML(self, compiler, m32=False):

        if m32:
            log.error("ERROR: m32 not supported yet for ACML.")

        # prepare toolkit for AMD Core Math Library (ACML)
        deps = [{'name': 'ACML'}, {'name': 'BLACS'}, {'name': 'ScaLAPACK'}]
        self._addDependencyVariables(deps)

        self.vars['LIBBLAS'] = "%(acml)s/%(comp)s64/lib/libacml_mv.a " \
                               "%(acml)s/%(comp)s64/lib/libacml.a -lpthread" % {'comp':compiler, 'acml':os.environ['SOFTROOTACML']}

    def prepareIMKL(self, m32=False):
        """ Prepare toolkit for IMKL: Intel Math Kernel Library """

        mklRoot = os.getenv('MKLROOT')
        if not mklRoot:
            log.error("MKLROOT not found in environment")

        # For more inspiration: see http://software.intel.com/en-us/articles/intel-mkl-link-line-advisor/

        libsuffix = "_lp64"
        libsuffixsl = "_lp64"
        libdir = "em64t"
        if m32:
            libsuffix = ""
            libsuffixsl = "_core"
            libdir = "32"

        self.vars['LIBLAPACK'] = \
            "-Wl,--start-group %(mkl)s/lib/%(libdir)s/libmkl_intel%(libsuffix)s.a " \
            "%(mkl)s/lib/%(libdir)s/libmkl_sequential.a " \
            "%(mkl)s/lib/%(libdir)s/libmkl_core.a -Wl,--end-group" % {'mkl':mklRoot,
                                                                      'libdir':libdir,
                                                                      'libsuffix':libsuffix
                                                                     }
        self.vars['LIBBLAS'] = self.vars['LIBLAPACK']
        self.vars['LIBLAPACK_MT'] = \
            "-Wl,--start-group %(mkl)s/lib/%(libdir)s/libmkl_intel%(libsuffix)s.a " \
            "%(mkl)s/lib/%(libdir)s/libmkl_intel_thread.a " \
            "%(mkl)s/lib/%(libdir)s/libmkl_core.a -Wl,--end-group " \
            "-liomp5 -lpthread" % {'mkl':mklRoot,
                                   'libdir':libdir,
                                   'libsuffix':libsuffix
                                  }
        self.vars['LIBSCALAPACK'] = \
            "%(mkl)s/lib/%(libdir)s/libmkl_scalapack%(libsuffixsl)s.a " \
            "%(mkl)s/lib/%(libdir)s/libmkl_solver%(libsuffix)s_sequential.a " \
            "-Wl,--start-group  %(mkl)s/lib/%(libdir)s/libmkl_intel%(libsuffix)s.a " \
            "%(mkl)s/lib/%(libdir)s/libmkl_sequential.a " \
            "%(mkl)s/lib/%(libdir)s/libmkl_core.a " \
            "%(mkl)s/lib/%(libdir)s/libmkl_blacs_intelmpi%(libsuffix)s.a -Wl,--end-group" % {'mkl':mklRoot,
                                                                                            'libdir':libdir,
                                                                                            'libsuffix':libsuffix,
                                                                                            'libsuffixsl':libsuffixsl
                                                                                           }
        lib = self.vars['LIBSCALAPACK']
        lib = lib.replace('libmkl_solver%s_sequential' % libsuffix, 'libmkl_solver')
        lib = lib.replace('libmkl_sequential', 'libmkl_intel_thread') + ' -liomp5 -lpthread'
        self.vars['LIBSCALAPACK_MT'] = lib

        # Exact paths/linking statements depend on imkl version
        if LooseVersion(os.environ['SOFTVERSIONIMKL']) < LooseVersion('10.3'):
            if m32:
                mklld = ['lib/32']
            else:
                mklld = ['lib/em64t']
            mklcpp = ['include', 'include/fftw']
        else:
            if m32:
                log.error("32-bit libraries not supported yet for IMKL v%s (> v10.3)" % os.environ("SOFTROOTIMKL"))

            mklld = ['lib/intel64', 'mkl/lib/intel64']
            mklcpp = ['mkl/include', 'mkl/include/fftw']

            static_vars = ['LIBBLAS', 'LIBLAPACK', 'LIBLAPACK_MT', 'LIBSCALAPACK', 'LIBSCALAPACK_MT']
            for var in static_vars:
                self.vars[var] = self.vars[var].replace('/lib/em64t/', '/mkl/lib/intel64/')

        # Linker flags
        self._flagsForSubdirs(mklRoot, mklld, flag="-L%s", varskey="LDFLAGS")
        self._flagsForSubdirs(mklRoot, mklcpp, flag="-I%s", varskey="CPPFLAGS")

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
                log.warning("Directory %s was not found" % directory)

        if not varskey in self.vars:
            self.vars[varskey] = ''
        self.vars[varskey] += ' ' + ' '.join(flags)

