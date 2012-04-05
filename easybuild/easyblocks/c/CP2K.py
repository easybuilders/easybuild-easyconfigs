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
import glob
import re
import os
import shutil
from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd

class CP2K(Application):

    def __init__(self, *args, **kwargs):
        Application.__init__(self, *args, **kwargs)

        self.cfg.update({'type':['popt',"Type of build (popt, psmp) (default: 'popt)"],
                         'typeopt':[True,"Enable optimization (default: True)"],
                         'libint':[True,"Use LibInt (default: True)"],
                         'modinc':['',"(default: '')"],
                         'modincprefix':['',"(default: '')"],
                         })

        self.typearch = None

        self.libintcompiler = None

        # this should be set to False for old versions of GCC (e.g. v4.1)
        self.compilerISO_C_BINDING = True

        # compiler options that need to be set in Makefile
        self.debug = ''
        self.fpic = ''

        self.libsmm = ''
        self.modincpath = ''
        self.openmp = ''

class OLD_CP2K(Application):
    """ Building CP2K """
    #typeversion = 'psmp'
    typeversion = 'popt'
    typeopt = True
    typearch = None

    libintcompiler = None
    libint = True
    compilerISO_C_BINDING = True
    
    def __init__(self,*args,**kwargs):
        """constructor, overwritten from Application to add extra config options and attributes"""
        Application.__init__(self, args,kwargs)
        
        self.cfg.update({'type':[None,"(default: None)"],
                         'typeopt':[None,"(default: None)"],
                         'libint':[None,"(default: None)"],
                         'modinc':['',"(default: '')"],
                         'modincprefix':['',"(default: '')"],
                         'extracflags':['',"Extra CFLAGS (default: '')"],
                         'extradflags':['',"Extra DFLAGS (default: '')"]
                         })
        
        self.libsmm = ''
        self.debug = ''
        self.fpic = ''
        self.extradflags = ''
        self.extracflags = ''
        self.modincpath = ''
        self.openmp = ''

    def prepmodinc(self):
        self.log.debug("Preparing module files")

        softrootimkl = os.getenv('SOFTROOTIMKL')
        if softrootimkl:
            modincpath = os.path.join(self.builddir, 'modinc')
            self.log.debug("Preparing module files in %s" % modincpath)

            try:
                os.mkdir(modincpath)
            except Exception, err:
                self.log.error("Failed to create directory for module include files: %s" % err)

            if type(self.getcfg("modinc")) == list:
                modfiles = [os.path.join(softrootimkl, self.getcfg("modincprefix"),
                                          'include', x) for x in self.getcfg("modinc")]
            elif type(self.getcfg("modinc")) == bool:
                modfiles = glob.glob(os.path.join(softrootimkl, self.getcfg("modinc"), 
                                                  'include', '*.f90'))
            else:
                self.log.error("prepmodinc: Please specify either a boolean value " \
                               "or a list of files in modinc (found: %s)." % 
                               self.getcfg("modinc"))

            f77 = os.getenv('F77')
            for f in modfiles:
                if f77.endswith('ifort') :
                    cmd = "$F77 -module %s -c %s" % (modincpath, f)
                elif f77 in ['gfortran', 'mpif77'] :
                    cmd = "$F77 -J%s -c %s" % (modincpath, f)
                else:
                    self.log.error("prepmodinc: Unknown value specified for F77 (%s)" % f77)

                run_cmd(cmd, log_all=True, simple=True)

            return modincpath
        else:
            self.log.error("Don't know how to prepare modinc")

    def configure(self):
        """
        Configure step
        - build Libint wrapper
        - generate Makefile
        """

        # set compilers options according to toolkit config
        if self.tk.opts['debug']:
            self.debug = '-g'
        if self.tk.opts['pic']:
            self.fpic = "-fPIC"
            self.log.info("Using fPIC")

        self.extra_cflags = self.getcfg('extracflags')
        if self.extra_cflags:
            self.log.info("Using extra CFLAGS: %s" % self.extra_cflags)
        self.extra_dflags = self.getcfg('extradflags')
        if self.extra_dflags:
            self.log.info("Using extra DFLAGS: %s" % self.extra_dflags)

        #Libsmm support
        libsmm = os.environ.has_key('SOFTROOTLIBSMM')
        #needs locs, but also loaded modules
        #if locs.has_key('libsmm'):
        #    if locs['libsmm'] and not libsmm:
        #        self.log.error("Can't use libsmm. No SOFTROOTLIBSMM found.")
        if libsmm:
            libsmms = glob.glob(os.path.join(os.environ['SOFTROOTLIBSMM'], 'lib') + '/libsmm_*nn.a')
            self.extradflags += ' ' + ' '.join([os.path.basename(os.path.splitext(x)[0]).replace('lib', '-D__HAS_') for x in libsmms])
            self.libsmm = ' '.join(libsmms)
            self.log.debug('Using libsmm %s (extradflags %s)' % (self.libsmm, self.extradflags))

        
        if self.getcfg("modinc"):
            self.modincpath = self.prepmodinc()

        configurations = {
            'ictce': self.configureIctce, 'gmgfl': self.configureGmgfl,
            'gogfl': self.configureGogfl, 'gimkl': self.configureGimkl,
            'gqacml': self.configureGqacml, 'gmqacml' : self.configureGmqacml
        }
        if configurations.has_key(self.tk.name):
            options = configurations[self.tk.name]()
            makeInstructions = "graphcon.o: graphcon.F\n\t$(FC) -c $(FCFLAGS2) $<\n"
        else:
            self.log.error("Unable to configure %s" % self.tk.name)

        archfile = os.path.join(self.getcfg('startfrom'), 'arch', '%s.%s' % (self.typearch, self.getcfg('type')))
        try:
            txt = self._generateMakefile(options, makeInstructions)
            f = open(archfile, 'w')
            f.write(txt)
            f.close()
            self.log.info("Content of makefile (%s):\n%s" % (archfile, txt))
        except:
            self.log.error("Writing makefile %s failed" % archfile)

    def configureCommon(self, toolkit, openmp="-openmp"):
        self.typearch = "Linux-x86-64-%s" % toolkit

        if self.getcfg('type') == 'psmp':
            self.openmp = openmp
            

        if self.getcfg('typeopt'):
            optflags = 'OPT'
            regflags = 'OPT2'
        else:
            optflags = 'NOOPT'
            regflags = 'NOOPT'

        if os.getenv('SOFTROOTIMKL') or os.getenv('SOFTROOTFFTW'):
            fftflavour = 'W3'
        elif os.getenv('SOFTROOTACML'):
            fftflavour = 'ACML'
        else:
            self.log.error("Unknown FFT-library")

        options = {
            'FPIC': self.fpic,
            'DEBUG': self.debug,

            'FCFLAGS': '$(FCFLAGS%s)' % optflags,
            'FCFLAGS2': '$(FCFLAGS%s)' % regflags,

            'DFLAGS': ('-D__parallel -D__BLACS -D__SCALAPACK -D__FFTSG ' \
                       '-D__FFT%(fftflavour)s %(extradflags)s'
                       % {'fftflavour': fftflavour, 'extradflags': self.extradflags}),
            'CFLAGS': self.extracflags,
            'LIBS': os.environ['LIBS']
        }

        if self.getcfg('libint'):
            options['DFLAGS'] += ' -D__LIBINT'

            # Build libint-wrapper
            libint_wrapper = ''
            if not self.compilerISO_C_BINDING:
                options['DFLAGS'] += ' -D__HAS_NO_ISO_C_BINDING'

                libinttools_paths = ['libint_tools', 'tools/hfx_tools/libint_tools']
                libinttools_path = None
                for path in libinttools_paths:
                    path = os.path.join(self.getcfg('startfrom'), path)
                    if os.path.isdir(path):
                        libinttools_path = path
                        os.chdir(libinttools_path)
                if not libinttools_path:
                    self.log.error("No libinttools dir found")

                cmd = "%s -c libint_cpp_wrapper.cpp -I$SOFTROOTLIBINT/include" % self.libintcompiler
                if not run_cmd(cmd, log_all=True, simple=True):
                    self.log.error("Building the libint wrapper failed")
                libint_wrapper = '%s/libint_cpp_wrapper.o' % libinttools_path

            libint_version = os.environ['SOFTVERSIONLIBINT'].split('.')[0]
            if libint_version == '1':
                libint_libs = "$(LIBINTLIB)/libderiv.a $(LIBINTLIB)/libint.a $(LIBINTLIB)/libr12.a"
            elif libint_version == '2':
                libint_libs = "$(LIBINTLIB)/libint2.a"
            else:
                self.log.error("Don't know how to handle libint version %s" % libint_version)
            self.log.info("Using libint version %s" % (libint_version))

            options['LIBINTLIB'] = '$(SOFTROOTLIBINT)/lib'
            options['LIBS'] += ' -lstdc++ %s %s' % (libint_libs, libint_wrapper)

        return options

    def configureIctce(self):
        """
        Set ictce specific
        - return arch file txt
        """
        self.libintcompiler = "icc -O3 -xHOST"
        options = self.configureCommon('ictce')

        """
## A whole bunch of old build settings

##DFLAGS   = -D__INTEL -D__parallel -D__BLACS -D__SCALAPACK -D__FFTSG -D__FFTW3 -D__FFTMKL

## Does NOT build with -O0 option!!!
##FCFLAGS  = $(DFLAGS) -I$(INTEL_INC) -I$(INTEL_INCF) -O0 -fpp -free
##FCFLAGS2 = $(DFLAGS) -I$(INTEL_INC) -I$(INTEL_INCF) -O0 -fpp -free

## $(FFTW3LIB)/libfftw3_threads.a : FFTW3 build with OpenMP

##LDFLAGS  = $(FCFLAGS) -I$(INTEL_INC) -I$(INTEL_INCF) -I$(FFTW3INC) \
\t$(INTEL_LIB)/libfftw3xc_intel.a $(INTEL_LIB)/libfftw3xf_intel.a $(FFTW3LIB)/libfftw3.a \
\t-Wl,--start-group \
\t$(INTEL_LIB)/libmkl_cdft_core.a $(INTEL_LIB)/libmkl_scalapack_lp64.a $(INTEL_LIB)/libmkl_blacs_intelmpi_lp64.a \
\t$(INTEL_LIB)/libmkl_intel_lp64.a $(INTEL_LIB)/libmkl_intel_thread.a $(INTEL_LIB)/libmkl_core.a \
\t-Wl,--end-group \
\t$(INTEL_LIB)/libiomp5.a $(INTEL_LIB)/libguide.a -lpthread \
\t$(LIBINTLIBS)
## newer version of mkl includes fftw

## old libs
##LIBS = \
\t-Wl,--start-group \
\t$(INTEL_LIB)/libmkl_cdft_core.a $(INTEL_LIB)/libmkl_scalapack_lp64.a $(INTEL_LIB)/libmkl_blacs_intelmpi_lp64.a \
\t$(INTEL_LIB)/libmkl_intel_lp64.a $(INTEL_LIB)/libmkl_intel_thread.a $(INTEL_LIB)/libmkl_core.a \
\t-Wl,--end-group \
\t$(INTEL_LIB)/libiomp5.a $(INTEL_LIB)/libguide.a -lpthread \
\t$(LIBINTLIBS)

## End of old setting
"""
        options.update({
            'CC': 'mpiicc',
            'CPP': '',

            ## full debug: -g -traceback -check all -fp-stack-check
            ## openmp introduces 2 major differences
            ## -automatic is default: -noautomatic -auto-scalar
            ## some mem-bandwidth optimisation
            # -g links to mpi debug libs
            #FC       = mpiifort %(openmp)s -g
            #LD       = mpiifort %(openmp)s -g
            'FC': 'mpiifort %s' % self.openmp,
            'LD': 'mpiifort %s' % self.openmp,
            'AR': 'ar -r',

            'FFTW3INC': '$(SOFTROOTFFTW)/include',
            'FFTW3LIB': '$(SOFTROOTFFTW)/lib',

            'INTEL_INC': '$(MKLROOT)/include',
            'INTEL_INCF': '$(INTEL_INC)/fftw',

            'CPPFLAGS': '',

            ## -Vaxlib : older options
            'FREE': '-fpp -free',

            ## fp-model precise : problems
            #SAFE = -assume protect_parens -fp-model precise -ftz
            #SAFE = -assume protect_parens -ftz
            #SAFE = -no-fma -fltconsistency -assume protect_parens -ftz
            'SAFE': '-assume protect_parens -no-unroll-aggressive',
            #SAFE = -fno-inline-functions -mp

            'INCFLAGS': '$(DFLAGS) -I$(INTEL_INC) -I$(INTEL_INCF) -I%s' % self.modincpath,

            'FCFLAGSNOOPT': '$(DFLAGS) $(CFLAGS) -O0  $(FREE) $(FPIC) $(DEBUG)',
            'FCFLAGSOPT': '$(INCFLAGS) -O2 -xHOST -heap-arrays 64 -funroll-loops $(FREE) $(SAFE) $(FPIC) $(DEBUG)',
            'FCFLAGSOPT2': '$(INCFLAGS) -O1 -xHOST -heap-arrays 64 $(FREE) $(SAFE) $(FPIC) $(DEBUG)',

            'LDFLAGS': '$(INCFLAGS) -i-static',
            'OBJECTS_ARCHITECTURE': 'machine_intel.o',

            'LIBS': '$(LIBSCALAPACK) %s' % options['LIBS']
        })

        options['DFLAGS'] += ' -D__INTEL -D__FFTMKL'

        return options

    def configureGccBased(self, toolkit, openmp='-fopenmp'):
        """ Configure common GCC-settings """
        self.libintcompiler = "gcc -O3 -march=native"
        options = self.configureCommon(toolkit, openmp)

        options.update({
            'CC': 'mpicc -v',
            'CPP': '',

            ## full debug: -g -traceback -check all -fp-stack-check
            ## openmp introduces 2 major differences
            ## -automatic is default: -noautomatic -auto-scalar
            ## some mem-bandwidth optimisation
            ## -g links to MPI debug libs
            # 'FC': 'mpif77 -g',
            # 'LD': 'mpif77 -g',
            'FC': 'mpif77',
            'LD': 'mpif77',
            'AR': 'ar -r',

            'FFTW_INC': '$(SOFTROOTFFTW)/include',
            'CPPFLAGS': '',

            ## need this to prevent "Unterminated character constant beginning" errors
            'FREE': '-ffree-form -ffree-line-length-none',

            'FCFLAGSNOOPT': '$(DFLAGS) $(CFLAGS) -O0 $(FREE)',
            'FCFLAGSOPT': '$(DFLAGS) $(CFLAGS) -O2 -march=native -ffast-math ' \
                          '-funroll-loops -ftree-vectorize -fmax-stack-var-size=32768 $(FREE)',
            'FCFLAGSOPT2': '$(DFLAGS) $(CFLAGS) -O1 -march=native $(FREE)',

            'LDFLAGS': '$(FCFLAGS)',
            'OBJECTS_ARCHITECTURE': 'machine_gfortran.o',
        })

        options['DFLAGS'] += ' -D__GFORTRAN'

        return options

    def configureGimkl(self):
        """ Configure for gimkl toolkit: GCC+IMPI+IMKL """
        options = self.configureGccBased('gimkl')

        options['FC'] = "mpif77 -fc=gfortran %s" % self.openmp
        options['LD'] = "mpif77 -fc=gfortran %s" % self.openmp

        # GIMKL specific?
        options['INTEL_INC'] = '$(MKLROOT)/include'
        options['INTEL_INCF'] = '$(INTEL_INC)/fftw'
        options['DFLAGS'] += ' -D__FFTMKL'
        options['CFLAGS'] += ' $(SOFTVARCPPFLAGS) $(SOFTVARLDFLAGS) -I$(INTEL_INC) ' \
                            '-I$(INTEL_INCF) -I%s $(FPIC) $(DEBUG)' % self.modincpath
        options['LIBS'] += ' %s $(LIBSCALAPACK)' % self.libsmm

        return options

    def configureGqacml(self):
        self.log.error("CP2K needs MPI-2, Qlogic MPI only supports MPI-1")

    def configureGmqacml(self):
        """ Configure for gmqacml toolkit: GCC+QlogicMPI+ACML """
        options = self.configureGccBased("gmqacml", openmp="_mp")

        options['ACML_INC'] = '$(SOFTROOTACML)/gfortran64%s/include' % self.openmp
        options['CFLAGS'] += ' $(SOFTVARCPPFLAGS) $(SOFTVARLDFLAGS) -I$(ACML_INC) ' \
                             '-I$(FFTW_INC) $(FPIC) $(DEBUG)'

        if os.getenv('SOFTROOTFFTW'):
            options['LIBS'] += ' -lfftw3'

        blas = os.environ['LIBBLAS'].replace('gfortran64', 'gfortran64%s' % self.openmp)
        options['LIBS'] += ' %s $(LIBSCALAPACK) %s' % (self.libsmm, blas)

        return options

    def configureGmgfl(self):
        """ Configure for gmgfl toolkit: GCC+LAPACK+GotoBLAS+FLAME+MVAPICH2 """
        options = self.configureGccBased('gmgfl')

        options['FC'] = 'mpif77 %s -g' % self.openmp
        options['LD'] = 'mpif77 %s -g' % self.openmp

        ## also needed somewhere if you split off the LIBS from LDFLAGS
        options['CFLAGS'] += ' $(SOFTVARCPPFLAGS) $(SOFTVARLDFLAGS) $(FPIC) $(DEBUG)'

        ## $(FFTW3LIB)/libfftw3_threads.a : FFTW3 build with OpenMP
        ## with -static: need -Wl,--whole-archive -lpthread -Wl,--no-whole-archive (but also static blcr lib)
        ##libs=-lfftw3 -lscalapack -lblacsF77init -lblacs -llapack2flame -lflame -llapack -lgoto -lpthread
        options['LIBS'] += ' -lfftw3 $(LIBSCALAPACK) -llapack -lgoto -lpthread'

        return options

    def configureGogfl(self):
        return self.configureGmgfl()

    def make(self):
        """
        Start the actual build
        - go into makefiles dir
        - patch Makefile
        """
        makefiles = os.path.join(self.getcfg('startfrom'), 'makefiles')
        try:
            os.chdir(makefiles)
        except:
            self.log.error("Can't change to makefiles dir %s: %s" % (makefiles))

        if self.getcfg('parallel'):
            ## backup
            try:
                shutil.move('Makefile', 'Makefile.orig')
                txt = open('Makefile.orig').read()

                r = re.compile(r"^PMAKE\s*=.*$", re.M)
                newtxt = r.sub("PMAKE\t= $(SMAKE) -j %s" % self.getcfg('parallel'), txt)

                f = open('Makefile', 'w')
                f.write(newtxt)
                f.close()
            except:
                self.log.error("Can't modify/write Makefile in %s" % makefiles)
        cmd = "make %s ARCH=%s VERSION=%s" % (self.getcfg('makeopts'), self.typearch, self.getcfg('type'))

        run_cmd(cmd + " clean", log_all=True, simple=True, log_output=True)
        run_cmd(cmd, log_all=True, simple=True, log_output=True)

    def makeInstall(self):
        """
        Create the installation in correct location
        - copy from exe to bin
        - copy tests
        """
        bindir = os.path.join(self.installdir, 'bin')
        exe = os.path.join(self.getcfg('startfrom'), 'exe/%s' % self.typearch)
        try:
            if not os.path.exists(bindir):
                os.makedirs(bindir)
            os.chdir(exe)
            for f in os.listdir(exe):
                if os.path.isfile(f):
                    shutil.copy2(f, bindir)
        except:
            self.log.error("Copying executables from %s to bin dir %s failed" % (exe, bindir))

        srctests = os.path.join(self.getcfg('startfrom'), 'tests')
        dsttests = os.path.join(self.installdir, 'tests')
        if os.path.exists(dsttests):
            self.log.info("Won't copy tests. Destination directory %s already exists" % (dsttests))
        else:
            try:
                shutil.copytree(srctests, dsttests)
            except:
                self.log.error("Copying tests from %s to %s failed" % (srctests, dsttests))

    def _generateMakefile(self, options, makeInstructions=''):
        text = "# Makefile generated by CP2K._generateMakefile, items might appear in random order\n"
        for key, value in options.iteritems():
            text += "%s = %s\n" % (key, value)
        return text + makeInstructions