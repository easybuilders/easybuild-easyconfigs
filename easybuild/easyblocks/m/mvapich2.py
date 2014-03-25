##
# Copyright 2009-2013 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
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

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import os

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM


class EB_MVAPICH2(ConfigureMake):
    """
    Support for building the MVAPICH2 MPI library.
    - some compiler dependent configure options
    """

    @staticmethod
    def extra_options():
        extra_vars = {
            'withchkpt': [False, "Enable checkpointing support (required BLCR)", CUSTOM],
            'withmpe': [False, "Build MPE routines", CUSTOM],
            'withhwloc': [False, "Enable support for using hwloc support for process binding", CUSTOM],
            'withlimic2': [False, "Enable LiMIC2 support for intra-node communication", CUSTOM],
            'debug': [False, "Enable debug build (which is slower)", CUSTOM],
            'rdma_type': ["gen2", "Specify the RDMA type (gen2/udapl)", CUSTOM],
            'blcr_path': [None, "Path to BLCR package", CUSTOM],
            'blcr_inc_path': [None, "Path to BLCR header files", CUSTOM],
            'blcr_lib_path': [None, "Path to BLCR library", CUSTOM],
        }
        return ConfigureMake.extra_options(extra_vars)

    def configure_step(self):

        # things might go wrong if a previous install dir is present, so let's get rid of it
        if not self.cfg['keeppreviousinstall']:
            self.log.info("Making sure any old installation is removed before we start the build...")
            super(EB_MVAPICH2, self).make_dir(self.installdir, True, dontcreateinstalldir=True)

        # additional configuration options
        add_configopts = []
        add_configopts.append('--with-rdma=%s' % self.cfg['rdma_type'])

        # use POSIX threads
        add_configopts.append('--with-thread-package=pthreads')

        if self.cfg['debug']:
            # debug build, with error checking, timing and debug info
            # note: this will affact performance
            add_configopts.append('--enable-fast=none')
        else:
            # optimized build, no error checking, timing or debug info
            add_configopts.append('--enable-fast')

        # enable shared libraries, using GCC and GNU ld options
        add_configopts.extend(['--enable-shared', '--enable-sharedlibs=gcc'])

        # enable Fortran 77/90 and C++ bindings
        add_configopts.extend(['--enable-f77', '--enable-fc', '--enable-cxx'])

        # MVAPICH configure script complains when F90 or F90FLAGS are set,
        # they should be replaced with FC/FCFLAGS instead
        for (envvar, new_envvar) in [("F90", "FC"), ("F90FLAGS", "FCFLAGS")]:
            envvar_val = os.getenv(envvar)
            if envvar_val:
                if not os.getenv(new_envvar):
                    env.setvar(new_envvar, envvar_val)
                    env.setvar(envvar, '')
                else:
                    self.log.error("Both %(ev)s and %(nev)s set, can I overwrite %(nev)s with %(ev)s (%(evv)s) ?" %
                                     {
                                      'ev': envvar,
                                      'nev': new_envvar,
                                      'evv': envvar_val
                                     })

        # enable specific support options (if desired)
        if self.cfg['withmpe']:
            add_configopts.append('--enable-mpe')
        if self.cfg['withlimic2']:
            add_configopts.append('--enable-limic2')
        if self.cfg['withchkpt']:
            add_configopts.extend(['--enable-checkpointing', '--with-hydra-ckpointlib=blcr'])
        if self.cfg['withhwloc']:
            add_configopts.append('--with-hwloc')

        # pass BLCR paths if specified
        if self.cfg['blcr_path']:
            add_configopts.append('--with-blcr=%s' % self.cfg['blcr_path'])
        if self.cfg['blcr_inc_path']:
            add_configopts.append('--with-blcr-include=%s' % self.cfg['blcr_inc_path'])
        if self.cfg['blcr_lib_path']:
            add_configopts.append('--with-blcr-libpath=%s' % self.cfg['blcr_lib_path'])

        self.cfg.update('configopts', ' '.join(add_configopts))

        super(EB_MVAPICH2, self).configure_step()

    # make and make install are default

    def sanity_check_step(self):
        """
        Custom sanity check for MVAPICH2
        """
        custom_paths = {
                        'files': ["bin/%s" % x for x in ["mpicc", "mpicxx", "mpif77",
                                                         "mpif90", "mpiexec.hydra"]] +
                                 ["lib/lib%s" % y for x in ["fmpich", "mpichcxx", "mpichf90",
                                                            "mpich", "mpl", "opa"]
                                                 for y in ["%s.so"%x, "%s.a"%x]],
                        'dirs': ["include"]
                       }

        super(EB_MVAPICH2, self).sanity_check_step(custom_paths=custom_paths)
