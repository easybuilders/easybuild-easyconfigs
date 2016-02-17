##
# Copyright 2009-2016 Ghent University, Forschungszentrum Juelich
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
EasyBuild support for building and installing the MPICH MPI library and derivatives, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Damian Alvarez (Forschungszentrum Juelich)
"""

import os

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_MPICH(ConfigureMake):
    """
    Support for building the MPICH MPI library and derivatives.
    - basically redefinition of environment variables
    """

    # There is a number of configuration options that are typically needed that are not present
    # here. The reason is that this easyblock is intended to be used as a parent for other 
    # easyblocks like MVAPICH2 and PSMPI. Not all of them support the same options, so they
    # are not included here.
    def configure_step(self):
        """Renaming of various environment variables needed for the configuration of MPICH"""

        # things might go wrong if a previous install dir is present, so let's get rid of it
        if not self.cfg['keeppreviousinstall']:
            self.log.info("Making sure any old installation is removed before we start the build...")
            super(EB_MPICH, self).make_dir(self.installdir, True, dontcreateinstalldir=True)

        # MPICH configure script complains when F90 or F90FLAGS are set,
        # they should be replaced with FC/FCFLAGS instead.
        # Additionally, there are a set of variables (FCFLAGS among them) that should not be set at configure time,
        # or they will leak in the mpix wrappers.
        # Specific variables to be included in the wrapper exists, but they changed between MPICH 3.1.4 and MPICH 3.2
        # and in a typical scenario we probably don't want them.
        env_vars = {
                "CFLAGS"   : "MPICHLIB_CFLAGS",
                "CPPFLAGS" : "MPICHLIB_CPPFLAGS",
                "CXXFLAGS" : "MPICHLIB_CXXFLAGS",
                "FCFLAGS"  : "MPICHLIB_FCFLAGS",
                "FFLAGS"   : "MPICHLIB_FFLAGS",
                "LDFLAGS"  : "MPICHLIB_LDFLAGS",
                "LIBS"     : "MPICHLIB_LIBS",
        }
        vars_to_unset = [ 'F90', 'F90FLAGS' ]
        for (envvar, new_envvar) in env_vars.items():
            envvar_val = os.getenv(envvar)
            if envvar_val:
                new_envvar_val = os.getenv(new_envvar)
                vars_to_unset += [envvar]
                if envvar_val == new_envvar_val:
                    self.log.debug("$%s == $%s, just defined $%s as empty", envvar, new_envvar, envvar)
                elif new_envvar_val is None:
                    env.setvar(new_envvar, envvar_val)
                else:
                    raise EasyBuildError("Both $%s and $%s set, can I overwrite $%s with $%s (%s) ?",
                                         envvar, new_envvar, new_envvar, envvar, envvar_val)
        env.unset_env_vars(vars_to_unset)

        super(EB_MPICH, self).configure_step()

    # make and make install are default

    def sanity_check_step(self, custom_paths=None):
        """
        Custom sanity check for MPICH
        """
        shlib_ext = get_shared_lib_ext()
        if custom_paths is None:
            custom_paths = {}
        
        custom_paths.setdefault('files', []).extend(['bin/%s' % x for x in ['mpicc', 'mpicxx', 'mpif77', 'mpif90' ]] +
                     ['lib/lib%s' % y for x in ['fmpich', 'mpichcxx', 'mpichf90', 'mpich', 'mpl', 'opa']
                                      for y in ['%s.%s' % (x, shlib_ext)]] +
                     ((custom_paths or {'files': []}).get('files') or []))
        custom_paths.setdefault('dirs', []).extend(['include'] + ((custom_paths or {'dirs': []}).get('dirs') or []))
        super(EB_MPICH, self).sanity_check_step(custom_paths=custom_paths)
