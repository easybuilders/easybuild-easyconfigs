##
# Copyright 2015-2016 Ghent University
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
EasyBuild support for installing Cray toolchains, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
@author: Guilherme Peretti Pezzi (CSCS)
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
        prgenv_name, prgenv_mod = None, None
        unload_info = {}

        # build dict with info for 'module swap' statements for dependencies,
        # i.e. a mapping of full module name to the module name to unload before loading
        # for example: {'fftw/3.3.4.1': 'fftw', 'cray-libsci/13.0.4': 'cray-libsci'}
        for dep in self.toolchain.dependencies:
            mod_name = dep['full_mod_name']
            # determine versionless module name, e.g. 'fftw/3.3.4.1' => 'fftw'
            dep_name = '/'.join(mod_name.split('/')[:-1])

            if dep_name.startswith('PrgEnv-'):
                prgenv_name = dep_name
                prgenv_mod = mod_name
            else:
                unload_info.update({mod_name: dep_name})

        if prgenv_name is None:
            raise EasyBuildError("Could not find a PrgEnv-* module listed as dependency: %s",
                                 self.toolchain.dependencies)

        self.log.debug("Swap info for dependencies of %s: %s", self.full_mod_name, unload_info)

        # load statement for all dependencies, including PrgEnv
        txt = super(CrayToolchain, self).make_module_dep(unload_info=unload_info)

        # include conditional swap for PrgEnv module,
        # to handle the case where another version the specified PrgEnv module is already loaded
        if self.module_generator.SYNTAX == 'Tcl':
            cond = "is-loaded %s" % prgenv_name
            body = "module swap %s %s" % (prgenv_name, prgenv_mod)
        elif self.module_generator.SYNTAX == 'Lua':
            cond = 'isloaded("%s")' % prgenv_name
            body = 'swap("%s", "%s")' % (prgenv_name, prgenv_mod)
        else:
            raise EasyBuildError("Unknown module syntax: %s", self.module_generator.SYNTAX)

        swap_prgenv = self.module_generator.conditional_statement(cond, body)

        # unload statements for PrgEnv-* modules must be included *first*
        comment = self.module_generator.comment("first, unload any PrgEnv module that may be loaded").strip()
        prgenv_unloads = ['', comment]
        for prgenv in KNOWN_PRGENVS:
            if prgenv not in prgenv_name:
                prgenv_unloads.append(self.module_generator.unload_module(prgenv).strip())

        comment = self.module_generator.comment("next, load toolchain components")

        txt = '\n'.join(prgenv_unloads) + '\n\n' + comment + swap_prgenv + txt

        return txt
