##
# Copyright 2009-2013 Ghent University
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
EasyBuild support for installing RPMs, implemented as an easyblock.

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Toon Willems (Ghent University)
"""

import glob
import os
import re
from distutils.version import LooseVersion
from os.path import expanduser

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.binary import Binary
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import run_cmd


class Rpm(Binary):
    """
    Support for installing RPM files.
    - sources is a list of rpms
    - installation is with --nodeps (so the sources list has to be complete)
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize class variables."""
        super(Rpm, self).__init__(*args, **kwargs)
        
        self.rebuildRPM = False

    @staticmethod
    def extra_options(extra_vars=None):
        """Extra easyconfig parameters specific to RPMs."""
        extra_vars = dict(EasyBlock.extra_options(extra_vars))
        extra_vars.update({
            'force': [False, "Use force", CUSTOM],
            'preinstall': [False, "Enable pre install", CUSTOM],
            'postinstall': [False, "Enable post install", CUSTOM],
            'makesymlinks': [[], "Create symlinks for listed paths", CUSTOM],  # supports glob
        })
        return EasyBlock.extra_options(extra_vars)

    def configure_step(self):
        """Custom configuration procedure for RPMs: rebuild RPMs for relocation if required."""

        # make sure that rpm is available
        if not 'rpm' in self.cfg['osdependencies']:
            self.cfg['osdependencies'].append('rpm')
            self.cfg.validate_os_deps()

        # determine whether RPMs need to be rebuilt to make relocation work
        cmd = "rpm --version"
        (out, _) = run_cmd(cmd, log_all=True, simple=False)
        
        rpmver_re = re.compile("^RPM\s+version\s+(?P<version>[0-9.]+).*")
        res = rpmver_re.match(out)
        self.log.debug("RPM version found: %s" % res.group())

        if res:
            ver = res.groupdict()['version']

            if LooseVersion(ver) >= LooseVersion('4.8.0'):
                self.rebuildRPM = True
                self.log.debug("Enabling rebuild of RPMs to make relocation work...")
        else:
            self.log.error("Checking RPM version failed, so just carrying on with the default behavior...")

        if self.rebuildRPM:
            self.rebuildRPMs()
    
    # when installing RPMs under a non-default path for e.g. SL6,
    # --relocate doesn't seem to work (error: Unable to change root directory: Operation not permitted)
    def rebuildRPMs(self):
        """Rebuild RPMs to make relocation work."""

        # make sure that rpm is available
        if not 'rpmrebuild' in self.cfg['osdependencies']:
            self.cfg['osdependencies'].append('rpmrebuild')
            self.cfg.validate_os_deps()

        rpmmacros = os.path.join(expanduser('~'), '.rpmmacros')
        if os.path.exists(rpmmacros):
            self.log.error("rpmmacros file %s found which will override any other settings, so exiting." % rpmmacros)

        rpmrebuild_tmpdir = os.path.join(self.builddir, "rpmrebuild")
        env.setvar("RPMREBUILD_TMPDIR", rpmrebuild_tmpdir)

        try:
            os.makedirs(rpmrebuild_tmpdir)
            self.log.debug("Created RPMREBUILD_TMPDIR dir %s" % rpmrebuild_tmpdir)
        except OSError, err:
            self.log.error("Failed to create RPMREBUILD_TMPDIR dir %s: %s" % (rpmrebuild_tmpdir, err))

        rpms_path = os.path.join(self.builddir, 'rebuiltRPMs')
        try:
            os.makedirs(rpms_path)
        except OSError, err:
            self.log.error("Failed to create %s: %s" % (rpms_path, err))

        for rpm in self.src:
            cmd = ' '.join([
                "rpmrebuild -v",
                """--change-spec-whole='sed -e "s/^BuildArch:.*/BuildArch:    x86_64/"'""",
                """--change-spec-whole='sed -e "s/^Prefix:.*/Prefix:    \//"'""",
                """--change-spec-whole='sed -e "s/^\(.*:[ ]\+\..*\)/#ERROR \1/"'""",
                "--notest-install",
                "-p -d",
                rpms_path,
                rpm['path'],
            ])
            run_cmd(cmd, log_all=True, simple=True)

        self.oldsrc = self.src
        self.src = []
        for rpm in os.listdir(os.path.join(rpms_path, 'x86_64')):
            self.src.append({
                             'name': rpm,
                             'path': os.path.join(rpms_path, 'x86_64', rpm)
                            })
        self.log.debug("oldsrc: %s, src: %s" % (self.oldsrc, self.src))

    def install_step(self):
        """Custom installation procedure for RPMs into a custom prefix."""
        try:
            os.chdir(self.installdir)
            os.mkdir('rpm')
        except:
            self.log.error("Can't create rpm dir in install dir %s" % self.installdir)

        cmd = "rpm --initdb --dbpath /rpm --root %s" % self.installdir

        run_cmd(cmd, log_all=True, simple=True)

        force=''
        if self.cfg['force']:
            force = '--force'

        postinstall = '--nopost'
        if self.cfg['postinstall']:
            postinstall = ''
        preinstall = '--nopre'
        if self.cfg['preinstall']:
            preinstall = ''

        if self.rebuildRPM:
            cmd_tpl = "rpm -i --dbpath %(inst)s/rpm %(force)s --relocate /=%(inst)s " \
                      "%(pre)s %(post)s --nodeps %(rpm)s"
        else:
            cmd_tpl = "rpm -i --dbpath /rpm %(force)s --root %(inst)s --relocate /=%(inst)s " \
                      "%(pre)s %(post)s --nodeps %(rpm)s"

        # exception for user root:
        # --relocate is not necesarry -> --root will relocate more than enough
        # cmd_tpl = "rpm -i --dbpath /rpm %(force)s --root %(inst)s %(pre)s %(post)s --nodeps %(rpm)s"

        for rpm in self.src:
            cmd = cmd_tpl % {
                             'inst': self.installdir,
                             'rpm': rpm['path'],
                             'force': force,
                             'pre': preinstall,
                             'post': postinstall
                            }
            run_cmd(cmd, log_all=True, simple=True)

        for path in self.cfg['makesymlinks']:
            # allow globs, always use first hit.
            # also verify links existince
            realdirs = glob.glob(path)
            if realdirs:
                if len(realdirs) > 1:
                    self.log.debug("More then one match found for symlink glob %s, using first (all: %s)" % (path, realdirs))
                os.symlink(realdirs[0], os.path.join(self.installdir, os.path.basename(path)))
            else:
                self.log.debug("No match found for symlink glob %s." % path)

    def make_module_req_guess(self):
        """Add common PATH/LD_LIBRARY_PATH paths found in RPMs to list of guesses."""

        guesses = super(Rpm, self).make_module_req_guess()

        guesses.update({
                        'PATH': guesses.get('PATH', []) + ['usr/bin', 'sbin', 'usr/sbin'],
                        'LD_LIBRARY_PATH': guesses.get('LD_LIBRARY_PATH', []) + ['usr/lib', 'usr/lib64'],
                        'MANPATH': guesses.get('MANPATH', []) + ['usr/share/man'],
                       })

        return guesses

