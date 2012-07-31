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
import shutil
import tempfile

from distutils.version import LooseVersion

from easybuild.easyblocks.i.intelbase import IntelBase
from easybuild.tools.filetools import run_cmd
from easybuild.tools.modules import Modules

import easybuild.tools.environment as env

class Imkl(IntelBase):
    """
    Class that can be used to install mkl
    - tested with 10.2.1.017
    -- will fail for all older versions (due to newer silent installer)
    """

    def __init__(self, *args, **kwargs):
        """Constructor, adds extra config options"""
        IntelBase.__init__(self, args, kwargs)

        self.cfg.update({'interfaces':[True, "Indicates whether interfaces should be built (default: True)"]})

    def configure(self):
        IntelBase.configure(self)

        if os.getenv('MKLROOT'):
            self.log.error("Found MKLROOT in current environment, which may cause problems...")

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for
        """
        if LooseVersion(self.version()) >= LooseVersion('10.3'):
            if self.getcfg('m32'):
                self.log.error("32-bit not supported yet for IMKL v%s (>= 10.3)" % self.version())
            return {
                    'PATH':['bin', 'mkl/bin', 'mkl/bin/intel64', 'composerxe-2011/bin'],
                    'LD_LIBRARY_PATH':['lib/intel64', 'mkl/lib/intel64'],
                    'LIBRARY_PATH':['lib/intel64', 'mkl/lib/intel64'],
                    'MANPATH':['man', 'man/en_US'],
                    'CPATH':['mkl/include', 'mkl/include/fftw'],
                    'FPATH':['mkl/include', 'mkl/include/fftw']
                   }
        else:
            if self.getcfg('m32'):
                return {
                    'PATH':['bin', 'bin/ia32', 'tbb/bin/ia32'],
                    'LD_LIBRARY_PATH':['lib', 'lib/32'],
                    'LIBRARY_PATH':['lib', 'lib/32'],
                    'MANPATH':['man', 'share/man', 'man/en_US'],
                    'CPATH':['include'],
                    'FPATH':['include']
                   }
            else:
                return {
                        'PATH':['bin', 'bin/intel64', 'tbb/bin/em64t'],
                        'LD_LIBRARY_PATH':['lib', 'lib/em64t'],
                        'LIBRARY_PATH':['lib', 'lib/em64t'],
                        'MANPATH':['man', 'share/man', 'man/en_US'],
                        'CPATH':['include'],
                        'FPATH':['include']
                       }

    def make_module_extra(self):
        """Overwritten from Application to add extra txt"""
        txt = IntelBase.make_module_extra(self)
        txt += "prepend-path\t%s\t\t%s\n" % ('INTEL_LICENSE_FILE', self.license)
        if self.getcfg('m32'):
            txt += "prepend-path\t%s\t\t$root/%s\n" % ('NLSPATH', 'idb/32/locale/%l_%t/%N')
        else:
            txt += "prepend-path\t%s\t\t$root/%s\n" % ('NLSPATH', 'idb/intel64/locale/%l_%t/%N')
        txt += "setenv\t%s\t\t$root\n" % ('MKLROOT')

        return txt

    def postproc(self):
        """
        The mkl directory structure has thoroughly changed as from version 10.3.
        Hence post processing is quite different in both situations
        """
        if LooseVersion(self.version()) >= LooseVersion('10.3'):
            #Add convenient wrapper libs
            #- form imkl 10.3

            if self.getcfg('m32'):
                self.log.error("32-bit not supported yet for IMKL v%s (>=10.3)" % self.version())

            extra = {
                   'libmkl.so':'GROUP (-lmkl_intel_lp64 -lmkl_intel_thread -lmkl_core)',
                   'libmkl_em64t.a':'GROUP (libmkl_intel_lp64.a libmkl_intel_thread.a libmkl_core.a)',
                   'libmkl_solver.a':'GROUP (libmkl_solver_lp64.a)',
                   'libmkl_scalapack.a':'GROUP (libmkl_scalapack_lp64.a)',
                   'libmkl_lapack.a':'GROUP (libmkl_intel_lp64.a libmkl_intel_thread.a libmkl_core.a)',
                   'libmkl_cdft.a':'GROUP (libmkl_cdft_core.a)'
                  }
            for fil, txt in extra.items():
                dest = os.path.join(self.installdir, 'mkl/lib/intel64', fil)
                if not os.path.exists(dest):
                    try:
                        f = open(dest, 'w')
                        f.write(txt)
                        f.close()
                        self.log.info("File %s written" % dest)
                    except:
                        self.log.exception("Can't write file %s" % (dest))

            #build the mkl interfaces (pic and no-pic)
            ## load the dependencies
            m = Modules()
            m.addModule(self.dep)
            m.load()

            if not self.getcfg('interfaces'):
                return

            #Build the interfaces
            #- blas95 and lapack95 need more work, ignore for now

            #lis1=['blas95','fftw2xc','fftw2xf','lapack95']
            # blas95 and lapack also need include/.mod to be processed
            lis1 = ['fftw2xc', 'fftw2xf']
            lis2 = ['fftw3xc', 'fftw3xf']
            lis3 = ['fftw2x_cdft', 'fftw3x_cdft']

            interfacedir = os.path.join(self.installdir, 'mkl/interfaces')
            try:
                os.chdir(interfacedir)
                self.log.info("Changed to interfaces directory %s" % interfacedir)
            except:
                self.log.exception("Can't change to interfaces directory %s" % (interfacedir))

            for i in lis1 + lis2 + lis3:
                if i in lis1:
                    ## Use INSTALL_DIR and CFLAGS and COPTS
                    cmd = "make -f makefile libintel64"
                if i in lis2:
                    ## Use install_to and CFLAGS
                    cmd = "make -f makefile libintel64 install_to=$INSTALL_DIR"
                if i in lis3:
                    ## Use INSTALL_DIR and SPEC_OPT
                    extramakeopts = ''
                    if os.getenv('SOFTROOTMPICH2'):
                        extramakeopts = 'mpi=mpich2'
                    cmd = "make -f makefile libintel64 %s" % extramakeopts


                for opt in ['', '-fPIC']:
                    try:
                        tmpbuild = tempfile.mkdtemp()
                        self.log.debug("Created temporary directory %s" % tmpbuild)
                    except:
                        self.log.exception("Creating temporary directory failed")

                    ## always set INSTALL_DIR, SPEC_OPT, COPTS and CFLAGS
                    env.set('INSTALL_DIR', tmpbuild)
                    env.set('SPEC_OPT', opt)
                    env.set('COPTS', opt)
                    env.set('CFLAGS', opt)

                    try:
                        intdir = os.path.join(interfacedir, i)
                        os.chdir(intdir)
                        self.log.info("Changed to interface %s directory %s" % (i, intdir))
                    except:
                        self.log.exception("Can't change to interface %s directory %s" % (i, intdir))

                    if not run_cmd(cmd, log_all=True, simple=True):
                        self.log.error("Building %s (opt: %s) failed" % (i, opt))

                    for fil in os.listdir(tmpbuild):
                        if opt == '-fPIC':
                            ## add _pic to filename
                            ff = fil.split('.')
                            newfil = '.'.join(ff[:-1]) + '_pic.' + ff[-1]
                        else:
                            newfil = fil
                        dest = os.path.join(self.installdir, 'mkl/lib/intel64', newfil)
                        try:
                            src = os.path.join(tmpbuild, fil)
                            if os.path.isfile(src):
                                shutil.move(src, dest)
                                self.log.info("Moved %s to %s" % (src, dest))
                        except:
                            self.log.exception("Failed to move %s to %s" % (src, dest))

                    try:
                        shutil.rmtree(tmpbuild)
                        self.log.debug('Removed temporary directory %s' % tmpbuild)
                    except:
                        self.log.exception("Removing temporary directory %s failed" % (tmpbuild))


        else:
            #Follow this procedure for mkl version lower than 10.3
            #Extra
            #- build the mkl interfaces (pic and no-pic)
            #- add wrapper libs
            #            Add convenient libs
            #- form imkl 10.1
            if self.getcfg('m32'):
                extra = {
                       'libmkl.so':'GROUP (-lmkl_intel -lmkl_intel_thread -lmkl_core)',
                       'libmkl_em64t.a':'GROUP (libmkl_intel.a libmkl_intel_thread.a libmkl_core.a)',
                       'libmkl_solver.a':'GROUP (libmkl_solver.a)',
                       'libmkl_scalapack.a':'GROUP (libmkl_scalapack_core.a)',
                       'libmkl_lapack.a':'GROUP (libmkl_intel.a libmkl_intel_thread.a libmkl_core.a)',
                       'libmkl_cdft.a':'GROUP (libmkl_cdft_core.a)'
                      }
            else:
                extra = {
                       'libmkl.so':'GROUP (-lmkl_intel_lp64 -lmkl_intel_thread -lmkl_core)',
                       'libmkl_em64t.a':'GROUP (libmkl_intel_lp64.a libmkl_intel_thread.a libmkl_core.a)',
                       'libmkl_solver.a':'GROUP (libmkl_solver_lp64.a)',
                       'libmkl_scalapack.a':'GROUP (libmkl_scalapack_lp64.a)',
                       'libmkl_lapack.a':'GROUP (libmkl_intel_lp64.a libmkl_intel_thread.a libmkl_core.a)',
                       'libmkl_cdft.a':'GROUP (libmkl_cdft_core.a)'
                      }
            for fil, txt in extra.items():
                if self.getcfg('m32'):
                    dest = os.path.join(self.installdir, 'lib/32', fil)
                else:
                    dest = os.path.join(self.installdir, 'lib/em64t', fil)
                if not os.path.exists(dest):
                    try:
                        f = open(dest, 'w')
                        f.write(txt)
                        f.close()
                        self.log.info("File %s written" % dest)
                    except:
                        self.log.exception("Can't write file %s" % (dest))

            ## load the dependencies
            m = Modules()
            m.addModule(self.dep)
            m.load()

            if not self.getcfg('interfaces'):
                return

            #Build the interfaces
            #- blas95 and lapack95 need more work, ignore for now
            #lis1=['blas95','fftw2xc','fftw2x_cdft','fftw2xf','lapack95']
            # blas95 and lapack also need include/.mod to be processed
            lis1 = ['fftw2xc', 'fftw2x_cdft', 'fftw2xf']
            lis2 = ['fftw3xc', 'fftw3xf']

            interfacedir = os.path.join(self.installdir, 'interfaces')
            try:
                os.chdir(interfacedir)
            except:
                self.log.exception("Can't change to interfaces directory %s" % (interfacedir))

            interfacestarget = "libem64t"
            if self.getcfg('m32'):
                interfacestarget = "lib32"

            for i in lis1 + lis2:
                if i in lis1:
                    ## Use INSTALL_DIR and SPEC_OPT
                    cmd = "make -f makefile %s" % interfacestarget
                if i in lis2:
                    ## Use install_to and CFLAGS
                    cmd = "make -f makefile %s install_to=$INSTALL_DIR" % interfacestarget


                for opt in ['', '-fPIC']:
                    try:
                        tmpbuild = tempfile.mkdtemp()
                        self.log.debug("Created temporary directory %s" % tmpbuild)
                    except:
                        self.log.exception("Creating temporary directory failed")

                    ## always set INSTALL_DIR, SPEC_OPT and CFLAGS
                    env.set('INSTALL_DIR', tmpbuild)
                    env.set('SPEC_OPT', opt)
                    env.set('CFLAGS', opt)

                    try:
                        intdir = os.path.join(interfacedir, i)
                        os.chdir(intdir)
                    except:
                        self.log.exception("Can't change to interface %s directory %s" % (i, intdir))

                    if not run_cmd(cmd, log_all=True, simple=True):
                        self.log.error("Building %s (opt: %s) failed" % (i, opt))

                    for fil in os.listdir(tmpbuild):
                        if opt == '-fPIC':
                            ## add _pic to filename
                            ff = fil.split('.')
                            newfil = '.'.join(ff[:-1]) + '_pic.' + ff[-1]
                        else:
                            newfil = fil
                        if self.getcfg('m32'):
                            dest = os.path.join(self.installdir, 'lib/32', newfil)
                        else:
                            dest = os.path.join(self.installdir, 'lib/em64t', newfil)
                        try:
                            src = os.path.join(tmpbuild, fil)
                            shutil.move(src, dest)
                            self.log.debug("Moved %s to %s" % (src, dest))
                        except:
                            self.log.exception("Failed to move %s to %s" % (src, dest))

                    try:
                        shutil.rmtree(tmpbuild)
                        self.log.debug('Removed temporary directory %s' % tmpbuild)
                    except:
                        self.log.exception("Removing temporary directory %s failed" % (tmpbuild))


    def sanitycheck(self):

        if not self.getcfg('sanityCheckPaths'):

            mklfiles = None
            mkldirs = None
            if LooseVersion(self.version()) >= LooseVersion('10.3'):
                if self.getcfg('m32'):
                    self.log.error("Sanity check for 32-bit not implemented yet for IMKL v%s (>= 10.3)" % self.version())
                else:
                    mklfiles = ["mkl/lib/intel64/libmkl.so", "mkl/include/mkl.h"]
                    mkldirs = ["bin", "mkl/bin", "mkl/bin/intel64", "compiler/lib/intel64",
                             "mkl/lib/intel64", "mkl/include"]
            else:
                if self.getcfg('m32'):
                    mklfiles = ["lib/32/libmkl.so", "include/mkl.h"]
                    mkldirs = ["lib/32", "include/32", "interfaces"]
                else:
                    mklfiles = ["lib/em64t/libmkl.so", "include/mkl.h"]
                    mkldirs = ["lib/em64t", "include/em64t", "interfaces"]

            self.setcfg('sanityCheckPaths', {'files':mklfiles,
                                            'dirs':mkldirs
                                           })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        IntelBase.sanitycheck(self)
