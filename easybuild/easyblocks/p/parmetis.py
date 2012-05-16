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
from easybuild.easyblocks.m.metis import METIS
from easybuild.tools.filetools import run_cmd
import os
import shutil

class ParMETIS(METIS):
    """
    Easyblock for the ParMETIS package
    Parmetis 
    """

    def configure(self):
        if self.version() < "4":
            return METIS.configure(self)
        #else
        #tested with 4.0.2, now actually requires cmake to be run first
        #for bot parmetis and metis
        for buildir in [ 'build' ] :
            cmd = 'cd %s && cmake .. %s -DCMAKE_INSTALL_PREFIX="%s" && cd %s' % \
                (buildir, self.getcfg('configopts'), self.installdir, self.getcfg('startfrom'))
            run_cmd(cmd, log_all=True, simple=True)



    def make(self):
        """
        make ParMETIS and Metis
        """
        paracmd = ''
        if self.getcfg('parallel'):
            paracmd = "-j %s" % self.getcfg('parallel')

        cmd = "%s make %s %s" % (self.getcfg('premakeopts'), paracmd, self.getcfg('makeopts'))
        if self.version() >= "4":
            cmd = "cd build && %s && cd %s " % (cmd, self.getcfg('startfrom'))
        #    #make metis seperatly
        #    cmdmetis = "cd metis/build && %s make %s %s && cd %s" % (self.getCfg('premakeopts'), paracmd, self.getCfg('makeopts'),self.getCfg('startfrom'))
        #    runrun(cmdmetis, logall=True, simple=True)
        run_cmd(cmd, log_all=True, simple=True)

    def make_install(self):

        includedir = os.path.join(self.installdir, 'include')
        libdir = os.path.join(self.installdir, 'lib')

        if self.version() >= "4":
            #includedir etc changed in v4, use a normal makeinstall
            cmd = "cd build && make install %s && cd %s" % (self.getcfg('installopts'),
                                                            self.getcfg('startfrom'))
            run_cmd(cmd, log_all=True, simple=True)
            # we build metis seperatlly now
            #cmd = "cd metis/build && make install %s && cd %s " % (self.getCfg('installopts'),self.getCfg('startfrom'))
            #runrun(cmd, logall=True, simple=True)
            try:
                src = os.path.join(self.getcfg('startfrom'), 'build/libmetis/libmetis.a')
                dst = os.path.join(libdir, 'libmetis.a')
                shutil.copy2(src, dst)
            except Exception, err:
                self.log.error("Copying files to installation dir failed: %s" % err)
            try:
                src = os.path.join(self.getcfg('startfrom'), 'build/metis/include/metis.h')
                dst = os.path.join(includedir, 'metis.h')
                shutil.copy2(src, dst)
            except Exception, err:
                self.log.error("Copying files to installation dir failed: %s" % err)

        else:

            try:
                os.mkdir(libdir)
                self.log.debug("Succesfully created directory %s" % libdir)
            except Exception, err:
                self.log.error("Failed to create directory %s: %s" % (libdir, err))

            try:
                os.mkdir(includedir)
                self.log.debug("Succesfully created directory %s" % includedir)
            except Exception, err:
                self.log.error("Failed to create directory %s: %s" % (includedir, err))

            try:
                for fil in ['libmetis.a', 'libparmetis.a']:
                    src = os.path.join(self.getcfg('startfrom'), fil)
                    dst = os.path.join(libdir, fil)
                    shutil.copy2(src, dst)
            except Exception, err:
                self.log.error("Copying files to installation dir failed: %s" % err)

            try:
                src = os.path.join(self.getcfg('startfrom'), 'parmetis.h')
                dst = os.path.join(includedir, 'parmetis.h')
                shutil.copy2(src, dst)
                # Some applications (SuiteSparse) can only use METIS (not ParMETIS), but header files are the same
                dst = os.path.join(includedir, 'metis.h')
                shutil.copy2(src, dst)
            except Exception, err:
                self.log.error("Copying files to installation dir failed: %s" % err)

        # Other applications depending on ParMETIS (SuiteSparse for one) look for both ParMETIS libraries
        # and headerfiles in the Lib directory (capital L). The following symlink are hence created.
        try:
            Libdir = os.path.join(self.installdir, 'Lib')
            os.symlink(libdir, Libdir)
            os.symlink(os.path.join(includedir, 'metis.h'), os.path.join(libdir, 'metis.h'))
            os.symlink(os.path.join(includedir, 'parmetis.h'),
                       os.path.join(libdir, 'parmetis.h'))
        except Exception, err:
            self.log.error("Something went wrong during symlink creation: %s" % err)
