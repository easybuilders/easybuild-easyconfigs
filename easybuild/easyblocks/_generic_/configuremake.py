##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
# Copyright 2012 Toon Willems
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
#
# http://github.com/hpcugent/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
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
"""

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import run_cmd


class EB_ConfigureMake(EasyBlock):
    """
    Support for building and installing applications with configure/make/make install
    """

    def configure_step(self, cmd_prefix=''):
        """
        Configure step
        - typically ./configure --prefix=/install/path style
        """

        cmd = "%s %s./configure --prefix=%s %s" % (self.getcfg('preconfigopts'), cmd_prefix,
                                                    self.installdir, self.getcfg('configopts'))

        (out, _) = run_cmd(cmd, log_all=True, simple=False)

        return out

    def build_step(self, verbose=False):
        """
        Start the actual build
        - typical: make -j X
        """

        paracmd = ''
        if self.getcfg('parallel'):
            paracmd = "-j %s" % self.getcfg('parallel')

        cmd = "%s make %s %s" % (self.getcfg('premakeopts'), paracmd, self.getcfg('makeopts'))

        (out, _) = run_cmd(cmd, log_all=True, simple=False, log_output=verbose)

        return out

    def test_step(self):
        """
        Test the compilation
        - default: None
        """

        if self.getcfg('runtest'):
            cmd = "make %s" % (self.getcfg('runtest'))
            (out, _) = run_cmd(cmd, log_all=True, simple=False)

            return out

    def install_step(self):
        """
        Create the installation in correct location
        - typical: make install
        """

        cmd = "make install %s" % (self.getcfg('installopts'))

        (out, _) = run_cmd(cmd, log_all=True, simple=False)

        return out

