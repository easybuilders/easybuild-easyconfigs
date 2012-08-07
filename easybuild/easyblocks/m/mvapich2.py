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
EasyBuild support for building and installing the MVAPICH2 MPI library, implemented as an easyblock
"""

import os

import easybuild.tools.environment as env
from easybuild.framework.application import Application


class MVAPICH2(Application):
    """
    Support for building the MVAPICH2 MPI library.
    - some compiler dependent configure options
    """

    def __init__(self, *args, **kwargs):
        Application.__init__(self, *args, **kwargs)

    def extra_options(self):
        extra_vars = {
                      'withchkpt': [False, "Enable checkpointing support (required BLCR) (default: False)"],
                      'withlimic2': [False, "Enable LiMIC2 support for intra-node communication (default: False)"],
                      'withmpe': [False, "Build MPE routines (default: False)"],
                      'debug': [False, "Enable debug build (which is slower) (default: False)"],
                      'rdma_type': ["gen2", "Specify the RDMA type (gen2/udapl) (default: gen2)"]
                     }
        return Application.extra_options(self, extra_vars)

    def configure(self):

        # things might go wrong if a previous install dir is present, so let's get rid of it
        if not self.getcfg('keeppreviousinstall'):
            self.log.info("Making sure any old installation is removed before we start the build...")
            Application.make_dir(self, self.installdir, True, dontcreateinstalldir=True)

        # additional configuration options
        add_configopts = '--with-rdma=%s ' % self.getcfg('rdma_type')

        # use POSIX threads
        add_configopts += '--with-thread-package=pthreads '

        if self.getcfg('debug'):
            # debug build, with error checking, timing and debug info
            # note: this will affact performance
            add_configopts += '--enable-fast=none '
        else:
            # optimized build, no error checking, timing or debug info
            add_configopts += '--enable-fast '

        # enable shared libraries, using GCC and GNU ld options
        add_configopts += '--enable-shared --enable-sharedlibs=gcc '

        # enable Fortran 77/90 and C++ bindings
        add_configopts += '--enable-f77 --enable-fc --enable-cxx '

        # MVAPICH configure script complains when F90 or F90FLAGS are set,
        # they should be replaced with FC/FCFLAGS instead
        for (envvar, new_envvar) in [("F90", "FC"), ("F90FLAGS", "FCFLAGS")]:
            envvar_val = os.getenv(envvar)
            if envvar_val:
                if not os.getenv(new_envvar):
                    env.set(new_envvar, envvar_val)
                    env.set(envvar, '')
                else:
                    self.log.error("Both %(ev)s and %(nev)s set, can I overwrite %(nev)s with %(ev)s (%(evv)s) ?" %
                                     {
                                      'ev': envvar,
                                      'nev': new_envvar,
                                      'evv': envvar_val
                                     })

        # enable specific support options (if desired)
        if self.getcfg('withmpe'):
            add_configopts += '--enable-mpe '
        if self.getcfg('withlimic2'):
            add_configopts += '--enable-limic2 '
        if self.getcfg('withchkpt'):
            add_configopts += '--enable-checkpointing --with-hydra-ckpointlib=blcr '

        self.updatecfg('configopts', add_configopts)

        Application.configure(self)

    # make and make install are default

    def sanitycheck(self):
        """
        Custom sanity check for MVAPICH2
        """
        if not self.getcfg('sanityCheckPaths'):

            self.setcfg('sanityCheckPaths',{
                                            'files': ["bin/%s" % x for x in ["mpicc", "mpicxx", "mpif77",
                                                                            "mpif90", "mpiexec.hydra"]] +
                                                     ["lib/lib%s" % y for x in ["fmpich", "mpichcxx", "mpichf90",
                                                                               "mpich", "mpl", "opa"]
                                                                     for y in ["%s.so"%x, "%s.a"%x]],
                                            'dirs': ["include"]
                                           })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        Application.sanitycheck(self)
