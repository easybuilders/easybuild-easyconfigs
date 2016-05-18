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
EasyBuild support for Perl module, implemented as an easyblock

@author: Jens Timmerman (Ghent University)
@author: Kenneth Hoste (Ghent University)
"""
import os

from easybuild.easyblocks.perl import EXTS_FILTER_PERL_MODULES, get_major_perl_version, get_site_suffix
from easybuild.framework.easyconfig import CUSTOM
from easybuild.framework.extensioneasyblock import ExtensionEasyBlock
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class PerlModule(ExtensionEasyBlock, ConfigureMake):
    """Builds and installs a Perl module, and can provide a dedicated module file."""

    @staticmethod
    def extra_options():
        """Easyconfig parameters specific to Perl modules."""
        extra_vars = {
            'runtest': ['test', "Run unit tests.", CUSTOM],  # overrides default
        }
        return ExtensionEasyBlock.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Initialize custom class variables."""
        super(PerlModule, self).__init__(*args, **kwargs)
        self.testcmd = None

    def install_perl_module(self):
        """Install procedure for Perl modules: using either Makefile.Pl or Build.PL."""
        # Perl modules have two possible installation procedures: using Makefile.PL and Build.PL
        # configure, build, test, install
        if os.path.exists('Makefile.PL'):
            run_cmd('%s perl Makefile.PL PREFIX=%s %s' % (self.cfg['preconfigopts'], self.installdir, self.cfg['configopts']))
            ConfigureMake.build_step(self)
            ConfigureMake.test_step(self)
            ConfigureMake.install_step(self)
        elif os.path.exists('Build.PL'):
            run_cmd('%s perl Build.PL --prefix %s %s' % (self.cfg['preconfigopts'], self.installdir, self.cfg['configopts']))
            run_cmd('%s perl Build build %s' % (self.cfg['prebuildopts'], self.cfg['buildopts']))
            run_cmd('perl Build test')
            run_cmd('%s perl Build install %s' % (self.cfg['preinstallopts'], self.cfg['installopts']))

    def run(self):
        """Perform the actual Perl module build/installation procedure"""

        if not self.src:
            raise EasyBuildError("No source found for Perl module %s, required for installation. (src: %s)",
                                 self.name, self.src)
        ExtensionEasyBlock.run(self, unpack_src=True)

        self.install_perl_module()

    def configure_step(self):
        """No separate configuration for Perl modules."""
        pass

    def build_step(self):
        """No separate build procedure for Perl modules."""
        pass

    def test_step(self):
        """No separate (standard) test procedure for Perl modules."""
        pass

    def install_step(self):
        """Run install procedure for Perl modules."""
        self.install_perl_module()

    def sanity_check_step(self, *args, **kwargs):
        """
        Custom sanity check for Perl modules
        """
        return ExtensionEasyBlock.sanity_check_step(self, EXTS_FILTER_PERL_MODULES, *args, **kwargs)

    def make_module_req_guess(self):
        """Customized dictionary of paths to look for with PERL*LIB."""
        majver = get_major_perl_version()
        sitearchsuffix = get_site_suffix('sitearch')
        sitelibsuffix = get_site_suffix('sitelib')

        guesses = super(PerlModule, self).make_module_req_guess()
        guesses.update({
            "PERL%sLIB" % majver: ['', sitearchsuffix, sitelibsuffix],
        })
        return guesses
