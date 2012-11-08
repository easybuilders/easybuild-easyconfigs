##
# Copyright 2012 Kenneth Hoste
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
EasyBuild support for ROOT, implemented as an easyblock
"""

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.filetools import run_cmd

class EB_ROOT(ConfigureMake):
    def configure_step(self):
        self.cfg['configopts'] = self.cfg['configopts'] + " --etcdir=%s/etc/root " % self.installdir
        super(ConfigureMake, self).configure_step()

    def make_module_extra(self):
        """
        Application specific extras
        """
        txt = ConfigureMake.make_module_extra(self)
        txt += self.moduleGenerator.setEnvironment("ROOTSYS", [""])
        txt += self.moduleGenerator.prependPaths("LD_LIBRARY_PATH",["/lib/root"])
        txt += self.moduleGenerator.prependPaths("PYTHONPATH",["/lib/root", "lib/root/python"])

        return txt

