##
# Copyright 2009-2016 Ghent University, Forschungszentrum Juelich
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
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
EasyBuild support for building and installing the MPICH MPI library and derivatives, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Damian Alvarez (Forschungszentrum Juelich)
@author: Xavier Besseron (University of Luxembourg)
"""
import os
from distutils.version import LooseVersion

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_MPICH(ConfigureMake):
    """
    Support for building the MPICH MPI library and derivatives.
    - basically redefinition of environment variables
    """

    @staticmethod
    def extra_options(extra_vars=None):
        """Define custom easyconfig parameters specific to MPICH."""
        extra_vars = ConfigureMake.extra_options(extra_vars)
        extra_vars.update({
            'debug': [False, "Enable debug build (which is slower)", CUSTOM],
        })
        return extra_vars

    # MPICH configure script complains when F90 or F90FLAGS are set,
    # they should be replaced with FC/FCFLAGS instead.
    # Additionally, there are a set of variables (FCFLAGS among them) that should not be set at configure time,
    # or they will leak in the mpix wrappers.
    # Specific variables to be included in the wrapper exists, but they changed between MPICH 3.1.4 and MPICH 3.2
    # and in a typical scenario we probably don't want them.
    def correct_mpich_build_env(self):
        """
        Method to correctly set the environment for MPICH and derivatives
        """
        env_vars = ['CFLAGS', 'CPPFLAGS', 'CXXFLAGS', 'FCFLAGS', 'FFLAGS', 'LDFLAGS', 'LIBS']
        vars_to_unset = ['F90', 'F90FLAGS']
        for envvar in env_vars:
            envvar_val = os.getenv(envvar)
            if envvar_val:
                new_envvar = 'MPICHLIB_%s' % envvar
                new_envvar_val = os.getenv(new_envvar)
                vars_to_unset.append(envvar)
                if envvar_val == new_envvar_val:
                    self.log.debug("$%s == $%s, just defined $%s as empty", envvar, new_envvar, envvar)
                elif new_envvar_val is None:
                    env.setvar(new_envvar, envvar_val)
                else:
                    raise EasyBuildError("Both $%s and $%s set, can I overwrite $%s with $%s (%s) ?",
                                         envvar, new_envvar, new_envvar, envvar, envvar_val)
        env.unset_env_vars(vars_to_unset)

    def add_mpich_configopts(self):
        """
        Method to add common configure options for MPICH-based MPI libraries
        """
        # additional configuration options
        add_configopts = []

        # use POSIX threads
        add_configopts.append('--with-thread-package=pthreads')

        if self.cfg['debug']:
            # debug build, with error checking, timing and debug info
            # note: this will affect performance
            add_configopts.append('--enable-fast=none')
        else:
            # optimized build, no error checking, timing or debug info
            add_configopts.append('--enable-fast')

        # enable shared libraries, using GCC and GNU ld options
        add_configopts.extend(['--enable-shared', '--enable-sharedlibs=gcc'])
        # enable static libraries
        add_configopts.extend(['--enable-static'])
        # enable Fortran 77/90 and C++ bindings
        add_configopts.extend(['--enable-f77', '--enable-fc', '--enable-cxx'])

        self.cfg.update('configopts', ' '.join(add_configopts))
 

    def configure_step(self, add_mpich_configopts=True):
        """
        Custom configuration procedure for MPICH

        * add common configure options for MPICH-based MPI libraries
        * unset environment variables that leak into mpi* wrappers, and define $MPICHLIB_* equivalents instead
        """

        # things might go wrong if a previous install dir is present, so let's get rid of it
        if not self.cfg['keeppreviousinstall']:
            self.log.info("Making sure any old installation is removed before we start the build...")
            super(EB_MPICH, self).make_dir(self.installdir, True, dontcreateinstalldir=True)
        
        if add_mpich_configopts:
            self.add_mpich_configopts()

        self.correct_mpich_build_env()

        super(EB_MPICH, self).configure_step()

    # make and make install are default

    def sanity_check_step(self, custom_paths=None, use_new_libnames=None, check_launchers=True):
        """
        Custom sanity check for MPICH
        """
        shlib_ext = get_shared_lib_ext()
        if custom_paths is None:
            custom_paths = {}

        if use_new_libnames is None:
            # cfr. http://git.mpich.org/mpich.git/blob_plain/v3.1.1:/CHANGES
            # MPICH changed its library names sinceversion 3.1.1
            use_new_libnames = LooseVersion(self.version) >= LooseVersion('3.1.1')

        # Starting MPICH 3.1.1, libraries have been renamed
        # cf http://git.mpich.org/mpich.git/blob_plain/v3.1.1:/CHANGES
        if use_new_libnames:
            libnames = ['mpi', 'mpicxx', 'mpifort']
        else:
            libnames = ['fmpich', 'mpichcxx', 'mpichf90', 'mpich', 'mpl', 'opa']

        binaries = ['mpicc', 'mpicxx', 'mpif77', 'mpif90']
        if check_launchers:
            binaries.extend(['mpiexec', 'mpiexec.hydra', 'mpirun'])

        bins = [os.path.join('bin', x) for x in binaries]
        headers = [os.path.join('include', x) for x in ['mpi.h', 'mpicxx.h', 'mpif.h']]
        libs = [os.path.join('lib', 'lib%s.%s' % (l, e)) for l in libnames for e in ['a', shlib_ext]]

        custom_paths.setdefault('dirs', []).extend(['bin', 'include', 'lib'])
        custom_paths.setdefault('files', []).extend(bins + headers + libs)

        super(EB_MPICH, self).sanity_check_step(custom_paths=custom_paths)
