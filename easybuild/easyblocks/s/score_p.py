##
# Copyright 2013 Ghent University
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
EasyBuild support for Score-P, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
@author: Bernd Mohr (Juelich Supercomputing Centre)
"""
import os

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.modules import get_software_root


class EB_Score_P(ConfigureMake):
    """Support for building and installing Score-P."""

    def configure_step(self, *args, **kwargs):
        """Configure Score-P build, set configure options for compiler, MPI and dependencies."""
        # compiler and MPI suite should always be specified -- MUCH quicker and SAVER than autodetect
        # --with-nocross-compiler-suite=(gcc|ibm|intel|pgi|studio)
        # --with-mpi=(bullxmpi|hp|ibmpoe|intel|intel2|intelpoe|lam|mpibull2|mpich|mpich2|mpich3|openmpi|
        #             platform|scali|sgimpt|sun)
        comp_opts = {
            toolchain.GCC: 'gcc',
            toolchain.INTELCOMP: 'intel',
        }
        comp_fam = self.toolchain.comp_family()
        if comp_fam in comp_opts:
            self.cfg.update('configopts', "--with-nocross-compiler-suite=%s" % comp_opts[comp_fam])
        else:
            self.log.error("Compiler family %s not supported yet (only: %s)" % (comp_fam, ', '.join(comp_opts.keys())))

        mpi_opts = {
            toolchain.INTELMPI: 'intel',  # intel2? intelpoe?
            toolchain.OPENMPI: 'openmpi',
            toolchain.MPICH: 'mpich',
            toolchain.MPICH2: 'mpich2',
        }
        mpi_fam = self.toolchain.mpi_family()
        if mpi_fam in mpi_opts:
            self.cfg.update('configopts', "--with-mpi=%s" % mpi_opts[mpi_fam])
        else:
            self.log.error("MPI family %s not supported yet (only: %s)" % (mpi_fam, ', '.join(mpi_opts.keys())))

        # auto-detection for dependencies mostly works fine, but hard specify paths anyway to have full control
        deps = {
            'binutils': ['--with-libbfd=%s/lib'],
            'Cube': ['--with-cube=%s/bin'],
            'CUDA': ['--with-libcudart=%s'],
            'OTF2': ['--with-otf2=%s/bin'],
            'OPARI2': ['--with-opari2=%s/bin'],
            'PAPI': ['--with-papi-header=%s/include', '--with-papi-lib=%s/lib'],
            'PDT': ['--with-pdt=%s/bin'],
        }
        for (dep_name, dep_opts) in deps.items():
            dep_root = get_software_root(dep_name)
            if dep_root:
                for dep_opt in dep_opts:
                    self.cfg.update('configopts', dep_opt % root)

        super(EB_Score_P, self).configure_step(*args, **kwargs)

    def sanity_check_step(self):
        """Custom sanity check for Score-P."""

        custom_paths = {
            'files': ["bin/scorep", "include/scorep/SCOREP_User.h",
                      ("lib64/libscorep_adapter_mpi_event.a", "lib/libscorep_adapter_mpi_event.a")],
            'dirs': [],
        }

        super(EB_Score_P, self).sanity_check_step(custom_paths=custom_paths)
