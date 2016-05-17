##
# Copyright 2009-2016 Ghent University
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
EasyBuild support for ROOT, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

from easybuild.framework.easyconfig import MANDATORY
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.run import run_cmd

class EB_ROOT(ConfigureMake):

    @staticmethod
    def extra_options():
        """
        Define extra options needed by Geant4
        """
        extra_vars = {
            'arch': [None, "Target architecture", MANDATORY],
        }
        return ConfigureMake.extra_options(extra_vars)

    def configure_step(self):
        """Custom configuration for ROOT, add configure options."""

        self.cfg.update('configopts', "--etcdir=%s/etc/root " % self.installdir)

        cmd = "%s ./configure %s --prefix=%s %s" % (self.cfg['preconfigopts'],
                                                    self.cfg['arch'],
                                                    self.installdir,
                                                    self.cfg['configopts'])

        run_cmd(cmd, log_all=True, log_ok=True, simple=True)

    def make_module_extra(self):
        """Custom extra module file entries for ROOT."""
        txt = super(EB_ROOT, self).make_module_extra()

        txt += self.module_generator.set_environment('ROOTSYS', self.installdir)
        txt += self.module_generator.prepend_paths('CPATH',['include/root'])
        txt += self.module_generator.prepend_paths('LD_LIBRARY_PATH',['lib/root'])
        txt += self.module_generator.prepend_paths('PYTHONPATH', ['lib/root', 'lib/root/python'])

        return txt

