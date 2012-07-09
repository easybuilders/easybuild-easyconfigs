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
import glob
import re
import os
import shutil
from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd

def det_interface(log, path):
    """Determine interface through xintface"""
    
    (out, _) = run_cmd(os.path.join(path,"xintface"), log_all=True, simple=False)
    
    intregexp = re.compile(".*INTFACE\s*=\s*-D(\S+)\s*")
    res = intregexp.search(out)
    if res:
        return res.group(1)
    else:
        log.error("Failed to determine interface, output for xintface: %s" % out)

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
            self.log.error("Copying %s to % failed: %s" % (src, dest, err))

    def make(self):

        # determine MPI base dir
        if os.getenv('SOFTROOTOPENMPI'):
            base = os.getenv('SOFTROOTOPENMPI')
            mpilib = '-L$(MPILIBdir) -lmpi_f77'
        elif os.getenv('SOFTROOTMVAPICH2'):
            base = os.getenv('SOFTROOTMVAPICH2')
            mpilib = '$(MPILIBdir)/libmpich.a $(MPILIBdir)/libfmpich.a $(MPILIBdir)/libmpl.a -lpthread'
        else:
            self.log.error("Don't know how to set MPI base dir, unknown MPI library used.")

        # common settings (for now)
        mpicc = 'mpicc'
        mpif77 = 'mpif77'

        opts = {
                'mpicc':mpicc,
                'mpif77':mpif77,
                'f77':os.getenv('F77'),
                'cc':os.getenv('CC'),
                'builddir':os.getcwd(),
                'base':base,
                'mpilib':mpilib
                }

        # determine interface and transcomm settings
        comm = ''
        interface = 'UNKNOWN'
        try:
            cwd = os.getcwd()
            os.chdir('INSTALL')

            # need to build
            cmd = "make"
            cmd += " CC='%(mpicc)s' F77='%(mpif77)s -I$(MPIINCdir)'  MPIdir=%(base)s" \
                   " MPILIB='%(mpilib)s' BTOPdir=%(builddir)s INTERFACE=NONE" % opts
            
            # determine interface using xintface
            run_cmd("%s xintface" % cmd, log_all=True, simple=True)

            interface = det_interface(self.log, "./EXE")

            # try and determine transcomm using xtc_CsameF77 and xtc_UseMpich
            if not comm:

                run_cmd("%s xtc_CsameF77" % cmd, log_all=True, simple=True)
                (out, _) = run_cmd("mpirun -np 2 ./EXE/xtc_CsameF77", log_all=True, simple=False)

                # get rid of first two lines, that inform about how to use this tool
                out = '\n'.join(out.split('\n')[2:])

                notregexp = re.compile("_NOT_")

                if not notregexp.search(out):
                    # if it doesn't say '_NOT_', set it
                    comm = "TRANSCOMM='-DCSameF77'"
                
                else:
                    (_, ec) = run_cmd("%s xtc_UseMpich" % cmd, log_all=False, log_ok=False, simple=False)
                    if ec == 0:
                        
                        (out, _) = run_cmd("mpirun -np 2 ./EXE/xtc_UseMpich", log_all=True, simple=False)
                        
                        if not notregexp.search(out):
                            
                            commregexp = re.compile('Set TRANSCOMM\s*=\s*(.*)$')
                            
                            res = commregexp.search(out)
                            if res:
                                # found how to set TRANSCOMM, so set it
                                comm = "TRANSCOMM='%s'" % res.group(1)
                            else:
                                # no match, set empty TRANSCOMM
                                comm = "TRANSCOMM=''"
                    else:
                        # if it fails to compile, set empty TRANSCOMM
                        comm = "TRANSCOMM=''"

            os.chdir(cwd)
        except OSError, err:
            self.log.error("Failed to determine interface and transcomm settings: %s" % err)

        opts.update({'comm':comm,
                     'int':interface,
                     'base':base,
                     })

        add_makeopts = ' MPICC=%(mpicc)s MPIF77=%(mpif77)s %(comm)s ' % opts
        add_makeopts += ' INTERFACE=%(int)s MPIdir=%(base)s BTOPdir=%(builddir)s mpi ' % opts

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

        src = os.path.join(self.getcfg('startfrom'), 'INSTALL', 'EXE', 'xintface')
        dest = os.path.join(self.installdir, 'bin')

        try:
            os.makedirs(dest)
            
            shutil.copy2(src, dest)
            
            self.log.debug("Copied %s to %s" % (src, dest))
            
        except OSError, err:
            self.log.error("Copying %s to installation dir %s failed: %s" % (src, dest, err))

    def sanitycheck(self):

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths',{'files':[fil for filptrn in ["blacs", "blacsCinit", "blacsF77init"]
                                                         for fil in ["lib/lib%s.a"%filptrn,
                                                                     "lib/%s_MPI-LINUX-0.a"%filptrn]] +
                                                    ["bin/xintface"],
                                            'dirs':[]
                                           })

            self.log.info("Customized sanity check paths: %s"%self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
