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
EasyBuild support for Perl, implemented as an easyblock

@author: Jens Timmerman (Ghent University)
@author: Kenneth Hoste (Ghent University)
"""

import os
import re

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.run import run_cmd

# perldoc -lm seems to be the safest way to test if a module is available, based on exit code
EXTS_FILTER_PERL_MODULES = ("perldoc -lm %(ext_name)s ", "")


class EB_Perl(ConfigureMake):
    """Support for building and installing Perl."""

    @staticmethod
    def extra_options():
        """Add extra config options specific to Perl."""
        extra_vars = {
            'use_perl_threads': [True, "Use internal Perl threads by means of the -Dusethreads compiler directive", CUSTOM],
        }
        return ConfigureMake.extra_options(extra_vars)

    def configure_step(self):
        """
        Configure Perl build: run ./Configure instead of ./configure with some different options
        """
        configopts = [
            self.cfg['configopts'],
            '-Dcc="{0}"'.format(os.getenv('CC')),
            '-Dccflags="{0}"'.format(os.getenv('CFLAGS')),
            '-Dinc_version_list=none',
        ]
        if self.cfg['use_perl_threads']:
            configopts.append('-Dusethreads')

        cmd = './Configure -de %s -Dprefix="%s"' % (' '.join(configopts), self.installdir)
        run_cmd(cmd, log_all=True, simple=True)

    def test_step(self):
        """Test Perl build via 'make test'."""
        # allow escaping with runtest = False
        if self.cfg['runtest'] is None or self.cfg['runtest']:
            if isinstance(self.cfg['runtest'], basestring):
                cmd = "make %s" % self.cfg['runtest']
            else:
                cmd = "make test"

            # specify locale to be used, to avoid that a handful of tests fail
            cmd = "export LC_ALL=C && %s" % cmd

            run_cmd(cmd, log_all=False, log_ok=False, simple=False)

    def prepare_for_extensions(self):
        """
        Set default class and filter for Perl modules
        """
        # build and install additional modules with PerlModule easyblock
        self.cfg['exts_defaultclass'] = "PerlModule"
        self.cfg['exts_filter'] = EXTS_FILTER_PERL_MODULES

    def sanity_check_step(self):
        """Custom sanity check for Perl."""
        majver = self.version.split('.')[0]
        custom_paths = {
            'files': [os.path.join('bin', x) for x in ['perl', 'perldoc']],
            'dirs': ['lib/perl%s/%s' % (majver, self.version), 'man']
        }
        super(EB_Perl, self).sanity_check_step(custom_paths=custom_paths)


def get_major_perl_version():
    """"
    Returns the major verson of the perl binary in the current path
    """
    cmd = "perl -MConfig -e 'print $Config::Config{PERL_API_REVISION}'"
    (perlmajver, _) = run_cmd(cmd, log_all=True, log_output=True, simple=False)
    return perlmajver

def get_site_suffix(tag):
    """
    Returns the suffix for site* (e.g. sitearch, sitelib)
    this will look something like /lib/perl5/site_perl/5.16.3/x86_64-linux-thread-multi
    so, e.g. sitearch without site prefix

    @tag: site tag to use, e.g. 'sitearch', 'sitelib'
    """
    perl_cmd = 'my $a = $Config::Config{"%s"}; $a =~ s/($Config::Config{"siteprefix"})//; print $a' % tag
    cmd = "perl -MConfig -e '%s'" % perl_cmd
    (sitesuffix, _) = run_cmd(cmd, log_all=True, log_output=True, simple=False)
    # obtained value usually contains leading '/', so strip it off
    return sitesuffix.lstrip(os.path.sep)

def get_sitearch_suffix():
    """Deprecated more specific version of get_site_suffix. Only here for backward compatibility."""
    _log = fancylogger.getLogger('Perl.get_sitearch_suffix', fname=False)
    _log.nosupport("Use get_site_suffix('sitearch') instead of get_sitearch_suffix()", "2.0")
