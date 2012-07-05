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
from distutils.version import LooseVersion
from easybuild.framework.application import Application
from easybuild.easyblocks.b.blacs import det_interface
from easybuild.easyblocks.l.lapack import get_blas_lib

class ScaLAPACK(Application):
    """
    Support for building and installing ScaLAPACK, both versions 1.x and 2.x
    - configure: copy SLmake.inc.example to SLmake.inc
    """
    def configure(self):
        src = os.path.join(self.getcfg('startfrom'), 'SLmake.inc.example')
        dest = os.path.join(self.getcfg('startfrom'), 'SLmake.inc')

        if not os.path.isfile(src):
            self.log.error("Can't fin source file %s" % src)

        if os.path.exists(dest):
            self.log.error("Destination file %s exists" % dest)

        try:
            shutil.copy(src, dest)
        except OSError, err:
            self.log.error("Symlinking %s to % failed: %s"%(src, dest, err))

        self.loosever = LooseVersion(self.version())

        # make sure required dependencies are available
        deps = ["LAPACK"]
        ## BLACS is only a dependency for ScaLAPACK versions prior to v2.0.0
        if self.loosever < LooseVersion("2.0.0"):
            deps.append("BLACS")
        for dep in deps:
            if not os.getenv('SOFTROOT%s' % dep.upper()):
                self.log.error("Dependency %s not available/loaded." % dep)

    def make(self):

        # MPI compiler commands
        if os.getenv('MPICC') and os.getenv('MPIF77') and os.getenv('MPIF90'):
            mpicc = os.getenv('MPICC')
            mpif77 = os.getenv('MPIF77')
            mpif90 = os.getenv('MPIF90')
        elif os.getenv('SOFTROOTOPENMPI') or os.getenv('SOFTROOTMVAPICH'):
            mpicc = 'mpicc'
            mpif77 = 'mpif77'
            mpif90 = 'mpif90'
        else:
            self.log.error("Don't know which compiler commands to use.")

        # set BLAS and LAPACK libs
        extra_makeopts = 'BLASLIB="%s -lpthread" LAPACKLIB=%s/lib/liblapack.a ' % (
                                                                                   get_blas_lib(self.log),
                                                                                   os.getenv('SOFTROOTLAPACK')
                                                                                   )

        # build procedure changed in v2.0.0
        if self.loosever < LooseVersion("2.0.0"):

            # determine interface
            interface = det_interface(self.log, os.path.join(os.getenv('SOFTROOTBLACS'),'bin'))

            blacsroot = os.getenv('SOFTROOTBLACS')

            # set build and BLACS dir correctly
            extra_makeopts += 'home=%s BLACSdir=%s ' % (self.getcfg('startfrom'), blacsroot)

            # set BLACS libs correctly
            for (var, lib) in [('BLACSFINIT', "F77init"), 
                               ('BLACSCINIT', "Cinit"), 
                               ('BLACSLIB', "")]:
                extra_makeopts += '%s=%s/lib/libblacs%s.a ' % (var, blacsroot, lib)

            # set compilers and options
            noopt = ''
            if self.tk.opts['noopt']:
                noopt += " -O0"
            if self.tk.opts['pic']:
                noopt += " -fPIC"
            extra_makeopts += 'F77="%(f77)s" CC="%(cc)s" NOOPT="%(noopt)s" CCFLAGS="-O3" ' % {
                                                                                              'f77':mpif77,
                                                                                              'cc':mpicc,
                                                                                              'noopt':noopt
                                                                                              }

            # set interface
            extra_makeopts += "CDEFS='-D%s -DNO_IEEE $(USEMPI)' " % interface

        else:

            # determine interface
            if os.getenv('SOFTROOTOPENMPI') or os.getenv('SOFTROOTMVAPICH2'):
                interface = 'Add_'
            else:
                self.log.error("Don't know which interface to pick for the MPI library being used.")

            # set compilers and options
            extra_makeopts += 'FC="%(fc)s" CC="%(cc)s" ' % {
                                                            'fc':mpif90,
                                                            'cc':mpicc,
                                                            }

            # set interface
            extra_makeopts += 'CDEFS="-D%s" ' % interface

        # update make opts, and make
        self.updatecfg('makeopts', extra_makeopts)

        Application.make(self)

    def make_install(self):

        src = os.path.join(self.getcfg('startfrom'), 'libscalapack.a')
        dest = os.path.join(self.installdir, 'lib')

        try:
            os.makedirs(dest)
            shutil.copy2(src,dest)
        except OSError, err:
            self.log.error("Copying %s to installation dir %s failed: %s"%(src, dest, err))

    def sanitycheck(self):

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths',{'files':["lib/libscalapack.a"],
                                            'dirs':[]
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
