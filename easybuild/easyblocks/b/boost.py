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
from easybuild.framework.application import Application
from easybuild.tools.filetools import run_cmd
from easybuild.tools.modules import get_software_root

class Boost(Application):
    """Support for building Boost."""

    def __init__(self, *args, **kwargs):
        Application.__init__(self, args, kwargs)

        self.objdir = None

        self.cfg.update({'boost_mpi':[False, "Build mpi boost module (default: False)"]})

    def configure(self):
        """Configure Boost build using custom tools"""

        # mpi sanity check
        if self.getcfg('boost_mpi') and not self.toolkit().opts['usempi']:
            self.log.error("When enabling building boost_mpi, also enable the 'usempi' toolkit option.")

        # create build directory (Boost doesn't like being built in source dir)
        try:
            self.objdir = os.path.join(self.builddir, 'obj')
            os.mkdir(self.objdir)
            self.log.debug("Succesfully created directory %s" % self.objdir)
        except OSError, err:
            self.log.error("Failed to create directory %s: %s" % (self.objdir, err))

        # generate config depending on compiler used
        # FIXME: use toolkit_comp_family for this
        toolset = None
        if os.getenv('SOFTROOTICC'):
            toolset = 'intel-linux'
        elif os.getenv('SOFTROOTGCC'):
            toolset = 'gcc'
        else:
            self.log.error("Unknown compiler used, aborting.")

        cmd = "./bootstrap.sh --with-toolset=%s --prefix=%s" % (toolset, self.objdir)
        run_cmd(cmd, log_all=True, simple=True)

        if self.getcfg('boost_mpi'):

            self.toolkit().opts['usempi'] = True
            # configure the boost mpi module
            # http://www.boost.org/doc/libs/1_47_0/doc/html/mpi/getting_started.html
            # let Boost.Build know to look here for the config file
            f = open('user-config.jam', 'a')
            f.write("using mpi : %s ;" % os.getenv("MPICXX"))
            f.close()


    def make(self):
        """Build Boost with bjam tool."""

        bjamoptions = " --prefix=%s" % self.objdir

        # specify path for bzip2 if module is loaded
        bzip2 = get_software_root('bzip2')
        if bzip2:
            bjamoptions += " -sBZIP2_INCLUDE=%s/include" % bzip2
            bjamoptions += " -sBZIP2_LIBPATH=%s/lib" % bzip2


        if self.getcfg('boost_mpi'):

            self.log.info("Building boost_mpi library")

            bjammpioptions = "%s --user-config=user-config.jam --with-mpi" % bjamoptions

            # build mpi lib first

            # let bjam know about the user-config.jam file we created in the configure step
            run_cmd("./bjam %s" % bjammpioptions, log_all=True, simple=True)

            # boost.mpi was built, let's 'install' it now
            run_cmd("./bjam %s  install" % bjammpioptions, log_all=True, simple=True)

        # install remainder of boost libraries
        self.log.info("Installing boost libraries")

        cmd = "./bjam %s install" % bjamoptions
        run_cmd(cmd, log_all=True, simple=True)

    def make_install(self):
        """Install Boost by copying file to install dir."""

        self.log.info("Copying %s to installation dir %s" % (self.objdir, self.installdir))

        try:
            for f in os.listdir(self.objdir):
                src = os.path.join(self.objdir, f)
                dst = os.path.join(self.installdir, f)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
        except OSError, err:
            self.log.error("Copying %s to installation dir %s failed: %s" % (self.objdir, self.installdir, err))

    def sanitycheck(self):
        """Custom sanity check for Boost."""

        if not self.getcfg('sanityCheckPaths'):

            mpifs = []
            if self.getcfg('boost_mpi'):
                mpifs = ['lib/libboost_mpi.so']

            self.setcfg('sanityCheckPaths', {'files': mpifs + ['lib/libboost_%s.so' % x for x in ['python',
                                                                                                  'system']],
                                             'dirs':['include/boost']})

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)