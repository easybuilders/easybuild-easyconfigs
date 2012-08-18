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
EasyBuild support for building and installing ScaLAPACK, implemented as an easyblock
"""

import os
import shutil
from distutils.version import LooseVersion

import easybuild.tools.toolkit as toolkit
from easybuild.easyblocks.b.blacs import det_interface
from easybuild.easyblocks.l.lapack import get_blas_lib
from easybuild.framework.application import Application
from easybuild.tools.modules import get_software_root


class EB_ScaLAPACK(Application):
    """
    Support for building and installing ScaLAPACK, both versions 1.x and 2.x
    """

    def configure(self):
        """Configure ScaLAPACK build by copying SLmake.inc.example to SLmake.inc and checking dependencies."""

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
        # BLACS is only a dependency for ScaLAPACK versions prior to v2.0.0
        if self.loosever < LooseVersion("2.0.0"):
            deps.append("BLACS")
        for dep in deps:
            if not get_software_root(dep):
                self.log.error("Dependency %s not available/loaded." % dep)

    def make(self):
        """Build ScaLAPACK using make after setting make options."""

        # MPI compiler commands
        if os.getenv('MPICC') and os.getenv('MPIF77') and os.getenv('MPIF90'):
            mpicc = os.getenv('MPICC')
            mpif77 = os.getenv('MPIF77')
            mpif90 = os.getenv('MPIF90')
        elif self.toolkit().mpi_type() in [toolkit.OPENMPI, toolkit.MVAPICH2]:
            mpicc = 'mpicc'
            mpif77 = 'mpif77'
            mpif90 = 'mpif90'
        else:
            self.log.error("Don't know which compiler commands to use.")

        # set BLAS and LAPACK libs
        extra_makeopts = [
                          'BLASLIB="%s -lpthread"' % get_blas_lib(self.log), 
                          'LAPACKLIB=%s/lib/liblapack.a' % get_software_root('LAPACK')
                         ]

        # build procedure changed in v2.0.0
        if self.loosever < LooseVersion("2.0.0"):

            blacs = get_software_root('BLACS')

            # determine interface
            interface = det_interface(self.log, os.path.join(blacs, 'bin'))

            # set build and BLACS dir correctly
            extra_makeopts.append('home=%s BLACSdir=%s' % (self.getcfg('startfrom'), blacs))

            # set BLACS libs correctly
            for (var, lib) in [
                               ('BLACSFINIT', "F77init"),
                               ('BLACSCINIT', "Cinit"),
                               ('BLACSLIB', "")
                              ]:
                extra_makeopts.append('%s=%s/lib/libblacs%s.a' % (var, blacs, lib))

            # set compilers and options
            noopt = ''
            if self.toolkit().opts['noopt']:
                noopt += " -O0"
            if self.toolkit().opts['pic']:
                noopt += " -fPIC"
            extra_makeopts += [
                               'F77="%s"' % mpif77,
                               'CC="%s"' % mpicc,
                               'NOOPT="%s"' % noopt,
                               'CCFLAGS="-O3"'
                              ]

            # set interface
            extra_makeopts.append("CDEFS='-D%s -DNO_IEEE $(USEMPI)'" % interface)

        else:

            # determine interface
            if self.toolkit().mpi_type() in [toolkit.OPENMPI, toolkit.MVAPICH2]:
                interface = 'Add_'
            else:
                self.log.error("Don't know which interface to pick for the MPI library being used.")

            # set compilers and options
            extra_makeopts += [
                               'FC="%s"' % mpif90, 
                               'CC="%s"' % mpicc
                              ]

            # set interface
            extra_makeopts.append('CDEFS="-D%s"' % interface)

        # update make opts, and make
        self.updatecfg('makeopts', ' '.join(extra_makeopts))

        Application.make(self)

    def make_install(self):
        """Install by copying files to install dir."""

        src = os.path.join(self.getcfg('startfrom'), 'libscalapack.a')
        dest = os.path.join(self.installdir, 'lib')

        try:
            os.makedirs(dest)
            shutil.copy2(src,dest)
        except OSError, err:
            self.log.error("Copying %s to installation dir %s failed: %s" % (src, dest, err))

    def sanitycheck(self):
        """Custom sanity check for ScaLAPACK."""

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths',{
                                            'files': ["lib/libscalapack.a"],
                                            'dirs': []
                                           })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
