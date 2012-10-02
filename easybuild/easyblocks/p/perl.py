##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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
EasyBuild support for Perl, implemented as an easyblock
"""

import os
import shutil

from easybuild.easyblocks.confguremake import EB_ConfigureMake  #@UnresolvedImport
from easybuild.framework.extension import Extension
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import run_cmd, run_cmd_qa

class Perl(EB_ConfigureMake):
    """
    Support for building Perl.
    Configure with interactive 'Configure' script, and build/install with build_step/make install;
    then set up CPAN configuration and install build module to prepare modules installation
    """

    @staticmethod
    def extra_options():
        """Add Perl-specific easyconfig parameters."""
        extra_vars = [('exts_force_list', [[], "List of modules to force installation for (e.g. because of failing tests).", CUSTOM])]

        return EB_ConfigureMake.extra_options(extra_vars)

    def patch_step(self, beginpath=None):
        """Make configure script writeable before applying patches."""

        configfile = os.path.join(self.src[0]['finalpath'],"Configure")

        try:
            os.chmod(configfile, 0777)
            self.log.info("The Configure script %s has been made writable" % configfile)
        except OSError, err:
            self.log.error('Something went wrong while trying to make %s writable (%s).' % (configfile, err))

        EB_ConfigureMake.patch_step(self, beginpath=beginpath)

    def configure_step(self):
        """Configure Perl build using 'Configure' script."""

        cmd = "./Configure -d -Dprefix=%s -Dcc=%s %s"%(self.installdir, os.getenv('CC'), self.getcfg('configopts'))

        qanda = {"Press return or use a shell escape to edit config.sh:": ""}
        no_qa = ["First let's make sure your kit is complete.  Checking..."]

        run_cmd_qa(cmd, qanda, noqanda=no_qa, log_all=True, simple=True)

    # make and make_install should be fine for build/installation

    def prepare_for_extensions(self):
        """Set up for building/installing Perl modules that will be part of the Perl module being built."""

        self.setcfg('exts_template', "%s_%s.tar.gz")
        self.setcfg('exts_defaultclass', ["Perl", "DefaultPerlModule"])
        self.setcfg('exts_filter', ['perl -M%(get_name)s -e "exit(0)"', ""])

        # clean up .cpan directory in home directory if necessary
        homeCPAN = os.path.join(os.getenv('HOME'), '.cpan')
        if os.path.lexists(homeCPAN):
                if os.path.islink(homeCPAN):
                    os.remove(homeCPAN)
                else:
                    shutil.rmtree(homeCPAN)

                self.log.warning("Found directory %s, which is likely to cause trouble. " \
                                 "Removed it to continue the (module) installation." % homeCPAN)

        buildAndCache = os.path.join(self.builddir, 'cpan')

        # symlink default build and cache location
        os.mkdir(buildAndCache)
        os.symlink(buildAndCache, homeCPAN)

        cmd = "mkdir -p %(builddir)s/sources; cd %(builddir)s/sources; wget http://www.perl.org/CPAN/MIRRORED.BY" % {'builddir': buildAndCache}
        run_cmd(cmd, log_all=True, simple=True)

        qanda = {
                 'Would you like me to configure as much as possible automatically? [yes]': 'no',
                 'Shall we use it as the general CPAN build and cache directory?': 'no',
                 'CPAN build and cache directory? [%s/.cpan]'%os.environ['HOME']: buildAndCache,
                 'Select your continent (or several nearby continents) []': '4',
                 'Select your continent (or several nearby continents) [8]': '4',
                 'Select your country (or several nearby countries) []': '2',
                 'Select your country (or several nearby countries) [31]': '2',
                 "Select as many URLs as you like (by number), put them on one line, separated by blanks, hyphenated ranges allowed e.g. '1 4 5' or '7 1-4 8' []": '2',
                 '(or just hit RETURN to keep your previous picks) [5]': '',
                 "Enter 'h' for help.": 'o conf init connect_to_internet_ok urllist',
                 'If no urllist has been chosen yet, would you prefer CPAN.pm to connect to the built-in default sites without asking? (yes/no)? [no]': 'yes',
                 'Would you like me to automatically choose the best CPAN mirror sites for you? (This means connecting to the Internet and could take a couple minutes) [yes] ': 'no',
                 "Please remember to call 'o conf commit' to make the config permanent!": 'o conf commit',
                 "commit: wrote '%s/lib/perl5/%s/CPAN/Config.pm'"%(self.installdir,self.get_version()): 'q',
                 "commit: wrote '%s/.cpan/CPAN/MyConfig.pm'"%os.environ['HOME']: 'q',
                 "Would you like me to automatically choose some CPAN mirror sites for you? (This means connecting to the Internet) [yes]": 'yes'
                }
        # standard answer: use default setting
        stdqanda = {
                    r"[?:]+(\s+\[.*\])?":'',
                    "commit: wrote '%s.*/.cpan/CPAN/MyConfig.pm'" % os.environ['HOME']: 'q'
                    }

        no_qa = [
                 'Searching for the best CPAN mirrors \(please be patient\) [.]*',
                ]

        cmd = "perl -MCPAN -e shell"
        run_cmd_qa(cmd, qanda, stdqa=stdqanda, noqanda=no_qa, log_all=True, simple=False)

        cmd = "export AUTOMATED_TESTING=1; cpan Bundle::CPAN; cpan Module::Build"
        run_cmd(cmd, log_all=True, simple=True)

        cmd = 'perl -MCPAN -e shell'

        qanda = {
               "Enter 'h' for help.": 'o conf prefer_installer MB',
               "Please use 'o conf commit' to make the config permanent!": 'o conf commit',
               "commit: wrote '%s/lib/perl5/%s/CPAN/Config.pm'" % (self.installdir, self.get_version()): 'q',
               "commit: wrote '%s/.cpan/CPAN/MyConfig.pm'" % os.environ['HOME']: 'q',
               }

        no_qa = ['\nt\/.*','\n%s.*'%os.environ['CC'],
                 'CHECKSUMS']

        stdqanda = {
                    "commit: wrote '%s.*/.cpan/CPAN/MyConfig.pm'"%os.environ['HOME']: 'q'
                   }

        run_cmd_qa(cmd, qanda, stdqa=stdqanda, noqanda=no_qa, log_all=True, simple=True)

class DefaultPerlModule(Extension):
    
    def run(self):
        force=""
        if self.name in self.cfg['exts_force_list'][0]:
            force="-f"
        cmd='cpan %s install %s'%(force,self.get_name)
        run_cmd(cmd,log_all=True,simple=True)

class bioperl(Extension):

    def run(self):
        
        cmd='perl -MCPAN -e shell'
        
        qanda={"Enter 'h' for help.":"force install %s"%self.get_version,
               'Install [a]ll BioPerl scripts, [n]one, or choose groups [i]nteractively? [a]':'a',
               'Build install  -- OK':'q',
               "make_test FAILED but failure ignored because 'force' in effect":'q',
               'Install [a]ll optional external modules, [n]one, or choose [i]nteractively? [n]':'a',
               'Enter your choice:  [1]':'',
               'Do you want to install Ace::Browser?  [n]':'',
               'Press <enter> to see the detailed list.':'',
               "CPAN.pm: Going to build %s"%self.get_version:'a',
               'disabled':'a',
               "Do you want to run tests that require connection to servers across the internet (likely to cause some failures)? y/n [n] Please answer 'y' or 'n'.":'n',
               'cpan[2]>':'q',
               '############################# WARNING #############################':'a'}
        
        stdqanda={r"Do you want.*\[.*\]":''}
        
        no_qa=['\nt\/.*','\n%s.*'%os.environ['CC'],
                 'DONE',
                 'bp_translate_seq.pl',
                 'ok',
                 "Reading skip patterns from 'INSTALL.SKIP'.",
                 'UNIVERSAL->import is deprecated and will be removed in a future perl at Bio/Tree/TreeFunctionsI.pm line 94',
                 'CPAN.pm: Building .*',
                 'DEL.*',
                 '\.+',
                 'Running Build install',
                 "Creating new 'Build' script for 'BioPerl' get_version.*"
                ]
        
        run_cmd_qa(cmd,qanda,stdqa=stdqanda,noqanda=noqanda,log_all=True,simple=True)            
              
        self.log.debug("Module %s installed succesfully" % self.get_name)
