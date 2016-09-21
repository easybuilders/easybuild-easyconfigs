##
# Copyright 2015-2016 Ghent University
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
EasyBuild support for installing Cray toolchains, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
@author: Guilherme Peretti Pezzi (CSCS)
@author: Petar Forai (IMP/IMBA)
"""

from easybuild.easyblocks.generic.bundle import Bundle
from easybuild.tools.build_log import EasyBuildError


KNOWN_PRGENVS = ['PrgEnv-cray', 'PrgEnv-gnu', 'PrgEnv-intel', 'PrgEnv-pgi']


class CrayToolchain(Bundle):
    """
    Compiler toolchain: generate module file only, nothing to build/install
    """
    def make_module_dep(self):
        """
        Generate load/swap statements for dependencies in the module file
        """
        prgenv_mod = None

        # collect 'swap' statement for dependencies (except PrgEnv)
        swap_deps = []
        for dep in self.toolchain.dependencies:
            mod_name = dep['full_mod_name']
            # determine versionless module name, e.g. 'fftw/3.3.4.1' => 'fftw'
            dep_name = '/'.join(mod_name.split('/')[:-1])

            if mod_name.startswith('PrgEnv'):
                prgenv_mod = mod_name
            else:
                swap_deps.append(self.module_generator.swap_module(dep_name, mod_name).lstrip())

        self.log.debug("Swap statements for dependencies of %s: %s", self.full_mod_name, swap_deps)

        if prgenv_mod is None:
            raise EasyBuildError("Could not find a PrgEnv-* module listed as dependency: %s",
                                 self.toolchain.dependencies)

        # unload statements for other PrgEnv modules
        prgenv_unloads = ['']
        for prgenv in [prgenv for prgenv in KNOWN_PRGENVS if not prgenv_mod.startswith(prgenv)]:
            prgenv_unloads.append(self.module_generator.unload_module(prgenv).strip())

        # load statement for selected PrgEnv module (only when not loaded yet)
        prgenv_load = self.module_generator.load_module(prgenv_mod, recursive_unload=False)

        txt = '\n'.join(prgenv_unloads + [prgenv_load] + swap_deps)
        return txt
