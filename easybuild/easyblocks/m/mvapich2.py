##
# Copyright 2009-2016 Ghent University, Forschungszentrum Juelich
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
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
EasyBuild support for building and installing the MVAPICH2 MPI library, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Damian Alvarez (Forschungszentrum Juelich)
@author: Xavier Besseron (University of Luxembourg)
"""

from distutils.version import LooseVersion

from easybuild.easyblocks.mpich import EB_MPICH
from easybuild.framework.easyconfig import CUSTOM


class EB_MVAPICH2(EB_MPICH):
    """
    Support for building the MVAPICH2 MPI library.
    - some compiler dependent configure options
    """

    @staticmethod
    def extra_options():
        """Define custom easyconfig parameters specific to MVAPICH2."""
        extra_vars = {
            'withchkpt': [False, "Enable checkpointing support (required BLCR)", CUSTOM],
            'withmpe': [False, "Build MPE routines", CUSTOM],
            'withhwloc': [False, "Enable support for using hwloc support for process binding", CUSTOM],
            'withlimic2': [False, "Enable LiMIC2 support for intra-node communication", CUSTOM],
            'rdma_type': ["gen2", "Specify the RDMA type (gen2/udapl)", CUSTOM],
            'blcr_path': [None, "Path to BLCR package", CUSTOM],
            'blcr_inc_path': [None, "Path to BLCR header files", CUSTOM],
            'blcr_lib_path': [None, "Path to BLCR library", CUSTOM],
        }
        return EB_MPICH.extra_options(extra_vars)

    def configure_step(self):
        """Define custom configure options for MVAPICH2."""

        # additional configuration options
        add_configopts = []
        add_configopts.append('--with-rdma=%s' % self.cfg['rdma_type'])

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
            'files': ['bin/mpiexec.mpirun_rsh'],
        }

        # cfr. http://git.mpich.org/mpich.git/blob_plain/v3.1.1:/CHANGES
        # MVAPICH2 2.1 is based on MPICH 3.1.4
        use_new_libnames = LooseVersion(self.version) >= LooseVersion('2.1')

        super(EB_MVAPICH2, self).sanity_check_step(custom_paths=custom_paths, use_new_libnames=use_new_libnames)
