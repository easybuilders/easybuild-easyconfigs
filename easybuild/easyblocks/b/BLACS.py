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
import os
import shutil
from easybuild.framework.application import Application

class BLACS(Application):
    """
    Support for building/installing BLACS
    - configure: symlink BMAKES/Bmake.MPI-LINUX to Bmake.inc
    - make install: copy files
    """

    def configure(self):

        src = os.path.join(self.getcfg('startfrom'), 'BMAKES', 'Bmake.MPI-LINUX')
        dest = os.path.join(self.getcfg('startfrom'), 'Bmake.inc')

        if not os.path.isfile(src):
            self.log.error("Can't find source file %s" % src)

        if os.path.exists(dest):
            self.log.error("Destination file %s exists" % dest)

        try:
            shutil.copy(src, dest)
        except OSError, err:
            self.log.error("Symlinking %s to % failed: %s" % (src, dest, err))

    def make(self):

        # tweak make options

        # common settings(for now)
        mpicc = 'mpicc'
        mpif77 = 'mpif77'

        # MPI lib specific settings
        if os.getenv('SOFTROOTOPENMPI'):
            comm = 'UseMpi2'
            interface = 'f77IsF2C'
            base = os.getenv('SOFTROOTOPENMPI')
    
        elif os.getenv('SOFTROOTMVAPICH2'):
            comm = 'CSameF77'
            interface = 'Add_'
            base = os.getenv('SOFTROOTMVAPICH2')
    
        else:
            self.log.error("Support for obtaining specific settings for MPI library used not yet implemented.")

        opts = {
                'mpicc':mpicc,
                'mpif77':mpif77,
                'comm':comm,
                'int':interface,
                'base':base,
                'builddir':os.getcwd()
                }
        add_makeopts = ' MPICC=%(mpicc)s MPIF77=%(mpif77)s TRANSCOMMPI=%(comm)s ' % opts
        add_makeopts += ' INTERFACE=%(int)s MPIBASE=%(base)s BUILDDIR=%(builddir)s mpi ' % opts

        self.updatecfg('makeopts', add_makeopts)

        Application.make(self)

    def make_install(self):
        src = os.path.join(self.getcfg('startfrom'), 'LIB')
        dest = os.path.join(self.installdir, 'lib')

        try:
            os.makedirs(dest)
            os.chdir(src)

            for lib in glob.glob('*.a'):

                # copy file
                shutil.copy2(os.path.join(src, lib), dest)

                # create symlink with more standard name
                symlink_name = "lib%s.a" % lib.split('_')[0]
                os.symlink(os.path.join(dest, lib), os.path.join(dest, symlink_name))
                self.log.debug("Copied %s to %s and symlinked it to %s" % (lib, dest, symlink_name))

        except OSError, err:
            self.log.error("Copying %s/*.a to installation dir %s failed: %s"%(src, dest, err))

    def sanitycheck(self):

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths',{'files':[fil for filptrn in ["blacs", "blacsCinit", "blacsF77init"]
                                                         for fil in ["lib/lib%s.a"%filptrn,
                                                                     "lib/%s_MPI-LINUX-0.a"%filptrn]],
                                            'dirs':[]
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
