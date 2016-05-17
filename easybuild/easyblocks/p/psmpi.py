##
# Copyright 2016-2016 Ghent University, Forschungszentrum Juelich
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
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
EasyBuild support for building and installing the ParaStationMPI library, implemented as an easyblock

@author: Damian Alvarez (Forschungszentrum Juelich)
"""

import easybuild.tools.toolchain as toolchain

from distutils.version import LooseVersion
from easybuild.easyblocks.mpich import EB_MPICH
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root


class EB_psmpi(EB_MPICH):
    """
    Support for building the ParaStationMPI library.
    * Determines the compiler to be used based on the toolchain
    * Enables threading if required by the easyconfig
    * Sets extra MPICH options if required by the easyconfig
    """

    @staticmethod
    def extra_options(extra_vars=None):
        """Define custom easyconfig parameters specific to ParaStationMPI."""
        extra_vars = EB_MPICH.extra_options(extra_vars)

        # ParaStationMPI doesn't offer this build option, and forcing it in the MPICH build
        # can be potentially conflictive with other options set by psmpi configure script.
        del extra_vars['debug']

        extra_vars.update({
            'mpich_opts': [None, "Optional options to configure MPICH", CUSTOM],
            'threaded': [False, "Enable multithreaded build (which is slower)", CUSTOM],
        })
        return extra_vars

    # MPICH configure script complains when F90 or F90FLAGS are set,
    def configure_step(self):
        """
        Custom configuration procedure for ParaStationMPI.
        * Sets the correct options
        * Calls the MPICH configure_step, disabling the default MPICH options
        """

        comp_opts = {
            toolchain.GCC: 'gcc',
            toolchain.INTELCOMP: 'intel',
            # TODO: Include PGI as soon as it is available as toolchain
            #toolchain.PGI: 'pgi',
        }

        # Set confset
        comp_fam = self.toolchain.comp_family()
        if comp_fam in comp_opts:
            self.cfg.update('configopts', ' --with-confset=%s' % comp_opts[comp_fam])
        else:
            raise EasyBuildError("Compiler %s not supported. Valid options are: %s",
                                 comp_fam, ', '.join(comp_opts.keys()))

        # Enable threading, if necessary
        if self.cfg['threaded']:
            self.cfg.update('configopts', ' --with-threading')

        # Add extra mpich options, if any
        if self.cfg['mpich_opts'] is not None:
            self.cfg.update('configopts', ' --with-mpichconf="%s"' % self.cfg['mpich_opts'])

        # Lastly, set pscom related variables
        self.cfg.update('preconfigopts', ('PSCOM_LDFLAGS=-L{0}/lib '+
                'PSCOM_CPPFLAGS=-I{0}/include').format(get_software_root('pscom')))

        super(EB_psmpi, self).configure_step(add_mpich_configopts=False)

    # make and make install are default

    def sanity_check_step(self):
        """
        Disable the checking of the launchers for ParaStationMPI
        """
        # cfr. http://git.mpich.org/mpich.git/blob_plain/v3.1.1:/CHANGES
        # MPICH changed its library names sinceversion 3.1.1.
        # cfr. https://github.com/ParaStation/psmpi2/blob/master/ChangeLog
        # ParaStationMPI >= 5.1.1-1 is based on MPICH >= 3.1.3.
        # ParaStationMPI < 5.1.1-1 is based on MPICH < 3.1.1.
        use_new_libnames = LooseVersion(self.version) >= LooseVersion('5.1.1-1')

        super(EB_psmpi, self).sanity_check_step(use_new_libnames=use_new_libnames, check_launchers=False)
