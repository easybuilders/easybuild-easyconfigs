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
EasyBuild support for software that uses the GNU installation procedure,
i.e. configure/make/make install, implemented as an easyblock.

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Toon Willems (Ghent University)
"""

from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.run import run_cmd


class ConfigureMake(EasyBlock):
    """
    Support for building and installing applications with configure/make/make install
    """

    @staticmethod
    def extra_options(extra_vars=None):
        """Extra easyconfig parameters specific to ConfigureMake."""
        extra_vars = EasyBlock.extra_options(extra=extra_vars)
        extra_vars.update({
            'configure_cmd_prefix': ['', "Prefix to be glued before ./configure", CUSTOM],
            'prefix_opt': [None, "Prefix command line option for configure script ('--prefix=' if None)", CUSTOM],
            'tar_config_opts': [False, "Override tar settings as determined by configure.", CUSTOM],
        })
        return extra_vars

    def configure_step(self, cmd_prefix=''):
        """
        Configure step
        - typically ./configure --prefix=/install/path style
        """

        if self.cfg.get('configure_cmd_prefix'):
            if cmd_prefix:
                tup = (cmd_prefix, self.cfg['configure_cmd_prefix'])
                self.log.debug("Specified cmd_prefix '%s' is overruled by configure_cmd_prefix '%s'" % tup)
            cmd_prefix = self.cfg['configure_cmd_prefix']

        if self.cfg.get('tar_config_opts'):
            # setting am_cv_prog_tar_ustar avoids that configure tries to figure out
            # which command should be used for tarring/untarring
            # am__tar and am__untar should be set to something decent (tar should work)
            tar_vars = {
                'am__tar': 'tar chf - "$$tardir"',
                'am__untar': 'tar xf -',
                'am_cv_prog_tar_ustar': 'easybuild_avoid_ustar_testing'
            }
            for (key, val) in tar_vars.items():
                self.cfg.update('preconfigopts', "%s='%s'" % (key, val))

        prefix_opt = self.cfg.get('prefix_opt')
        if prefix_opt is None:
            prefix_opt = '--prefix='

        cmd = "%(preconfigopts)s %(cmd_prefix)s./configure %(prefix_opt)s%(installdir)s %(configopts)s" % {
            'preconfigopts': self.cfg['preconfigopts'],
            'cmd_prefix': cmd_prefix,
            'prefix_opt': prefix_opt,
            'installdir': self.installdir,
            'configopts': self.cfg['configopts'],
        }

        (out, _) = run_cmd(cmd, log_all=True, simple=False)

        return out

    def build_step(self, verbose=False, path=None):
        """
        Start the actual build
        - typical: make -j X
        """

        paracmd = ''
        if self.cfg['parallel']:
            paracmd = "-j %s" % self.cfg['parallel']

        cmd = "%s make %s %s" % (self.cfg['prebuildopts'], paracmd, self.cfg['buildopts'])

        (out, _) = run_cmd(cmd, path=path, log_all=True, simple=False, log_output=verbose)

        return out

    def test_step(self):
        """
        Test the compilation
        - default: None
        """

        if self.cfg['runtest']:
            cmd = "make %s" % (self.cfg['runtest'])
            (out, _) = run_cmd(cmd, log_all=True, simple=False)

            return out

    def install_step(self):
        """
        Create the installation in correct location
        - typical: make install
        """

        cmd = "%s make install %s" % (self.cfg['preinstallopts'], self.cfg['installopts'])

        (out, _) = run_cmd(cmd, log_all=True, simple=False)

        return out
