##
# Copyright 2013 Ghent University
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
EasyBuild support for Scalasca v1.x, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
@author: Bernd Mohr (Juelich Supercomputing Centre)
"""
import os
from distutils.version import LooseVersion

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root


class EB_Scalasca1(ConfigureMake):
    """Support for building and installing Scalasca v1.x."""

    def check_readiness_step(self):
        """Make sure this easyblock is applicable to the Scalasca version being built."""
        ver = LooseVersion(self.version)
        if ver >= LooseVersion('2.0') or ver < LooseVersion('1.0'):
            raise EasyBuildError("The %s easyblock should only be used for Scalasca v1.x; "
                                 "for Scalasca v2.0 and more recent, try the EB_Score_minus_P easyblock.",
                                 self.__class__.__name__)

        super(EB_Scalasca1, self).check_readiness_step()

    def configure_step(self, *args, **kwargs):
        """Configure Scalasca build, set configure options for compiler, MPI and dependencies."""
        # compiler and MPI suite should always be specified -- MUCH quicker and SAFER than autodetect
        # --compiler=(gnu|pgi|intel|path|ibm|sun|clang)
        # --mpi=(mpich|mpich2|mpich3|lam|openmpi|intel|intel2|hp|scali|mpibull2|bullxmpi|sun|ibmpoe|intelpoe)
        comp_opts = {
            toolchain.GCC: 'gnu',
            toolchain.INTELCOMP: 'intel',
        }
        comp_fam = self.toolchain.comp_family()
        if comp_fam in comp_opts:
            self.cfg.update('configopts', "--compiler=%s" % comp_opts[comp_fam])
        else:
            raise EasyBuildError("Compiler family %s not supported yet (only: %s)",
                                 comp_fam, ', '.join(comp_opts.keys()))

        mpi_opts = {
            toolchain.INTELMPI: 'intel2',  # intel: Intel MPI v1.x (ancient)
            toolchain.OPENMPI: 'openmpi',
            toolchain.MPICH: 'mpich3',  # In EB terms, MPICH means MPICH 3.x; MPICH 1.x is ancient and unsupported
            toolchain.MPICH2: 'mpich2',
        }
        mpi_fam = self.toolchain.mpi_family()
        if mpi_fam in mpi_opts:
            self.cfg.update('configopts', "--mpi=%s --enable-all-mpi-wrappers" % mpi_opts[mpi_fam])
        else:
            raise EasyBuildError("MPI family %s not supported yet (only: %s)", mpi_fam, ', '.join(mpi_opts.keys()))

        # auto-detection for dependencies mostly works fine, but hard specify paths anyway to have full control
        deps = {
            'binutils': ['--with-binutils=%s'],
            'OTF': ['--with-otf=%s'],
            'OPARI2': ['--with-opari2=%s'],
            'PAPI': ['--with-papi=%s'],
            'PDT': ['--with-pdt=%s'],
        }
        for (dep_name, dep_opts) in deps.items():
            dep_root = get_software_root(dep_name)
            if dep_root:
                for dep_opt in dep_opts:
                    self.cfg.update('configopts', dep_opt % dep_root)
        if get_software_root('Cube'):
            self.cfg.update('configopts', '--disable-gui')

        super(EB_Scalasca1, self).configure_step(*args, **kwargs)

    def build_step(self):
        """Build Scalasca using make, after stepping into the build dir."""
        build_dir_found = False
        try:
            for entry in os.listdir(os.getcwd()):
                if entry.startswith('build-linux-') and os.path.isdir(entry):
                    os.chdir(entry)
                    build_dir_found = True
                    self.log.info("Stepped into build dir %s" % entry)
        except OSError, err:
            raise EasyBuildError("Failed to step into build dir before starting actual build: %s", err)
        if not build_dir_found:
            raise EasyBuildError("Could not find build dir to step into.")
        super(EB_Scalasca1, self).build_step()
