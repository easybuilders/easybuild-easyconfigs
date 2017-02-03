##
# Copyright 2009-2017 Ghent University
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
EasyBuild support for Mono, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
from distutils.version import LooseVersion
import re
import os
import shutil
import sys

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.easyblocks.generic.rpm import Rpm
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import apply_regex_substitutions, read_file
from easybuild.tools.run import run_cmd


class EB_Mono(ConfigureMake, Rpm):
    """Support for building/installing Mono."""

    @staticmethod
    def extra_options(extra_vars=None):
        """Combine custom easyconfig parameters specific to ConfigureMake and Rpm generic easyblocks."""
        extra_vars = ConfigureMake.extra_options()
        return Rpm.extra_options(extra_vars=extra_vars)

    def __init__(self, *args, **kwargs):
        """Custom constructor for Mono easyblock, initialize custom class variables."""
        super(EB_Mono, self).__init__(*args, **kwargs)
        self.mono_srcs = []
        self.rpms = []

    def extract_step(self):
        """Custom extract step for Mono: don't try and extract any of the provided RPMs."""

        for src in self.src:
            if src['name'].endswith('.rpm'):
                self.rpms.append(src)
            else:
                self.mono_srcs.append(src)

        self.src = self.mono_srcs
        ConfigureMake.extract_step(self)

    def configure_step(self):
        """Dedicated configure step for Mono: install Mono from RPM (if provided), then run configure."""

        # install Mono from RPMs if provided (because we need Mono to build Mono)
        if self.rpms:

            # prepare path for installing RPMs in
            monorpms_path = os.path.join(self.builddir, "monorpms")
            try:
                os.makedirs(os.path.join(monorpms_path, 'rpm'))
            except OSError as err:
                raise EasyBuildError("Failed to create directories for installing Mono RPMs in: %s", err)

            self.src = self.rpms
            self.rebuildRPM = True

            # rebuild RPMs to make them relocatable
            Rpm.configure_step(self)

            # prepare to install RPMs
            self.log.debug("Initializing temporary RPM repository to install to...")
            cmd = "rpm --initdb --dbpath /rpm --root %s" % monorpms_path
            run_cmd(cmd, log_all=True, simple=True)

            # install RPMs one by one
            for rpm in self.src:
                self.log.debug("Installing RPM %s ..." % rpm['name'])
                if os.path.exists(rpm['path']):
                    cmd = ' '.join([
                        "rpm -i",
                        "--dbpath %(inst)s/rpm",
                        "--force",
                        "--relocate /=%(inst)s",
                        "--badreloc",
                        "--nodeps --nopost",
                        "%(rpm)s",
                    ]) % {
                        'inst': monorpms_path,
                        'rpm': rpm['path'],
                    }
                    run_cmd(cmd,log_all=True,simple=True)
                else:
                    raise EasyBuildError("RPM file %s not found", rpm['path'])

            # create patched version of gmcs command
            self.log.debug("Making our own copy of gmcs (one that works).")

            mygmcs_path = os.path.join(monorpms_path, 'usr', 'bin', 'mygmcs')
            try:
                shutil.copy(os.path.join(monorpms_path, 'usr' ,'bin', 'gmcs'), mygmcs_path)
            except OSError as err:
                raise EasyBuildError("Failed to copy gmcs to %s: %s", mygmcs_path, err)

            rpls = [
                ("exec /usr/bin/mono", "exec %s/usr/bin/mono" % monorpms_path),
                ("`/usr/bin/monodir`", "%s/usr/lib64/mono" % monorpms_path),
            ]
            apply_regex_substitutions(mygmcs_path, rpls)

            self.log.debug("Patched version of gmcs (%s): %s" % (mygmcs_path, read_file(mygmcs_path)))

            # initiate bootstrap: build/install Mono with installed RPMs to temporary path
            tmp_mono_path = os.path.join(self.builddir, "tmp_mono")
            self.log.debug("Build/install temporary Mono version in %s using installed RPMs..." % tmp_mono_path)

            par = ''
            if self.cfg['parallel']:
                par = "-j %s" % self.cfg['parallel']

            config_cmd = "%s ./configure --prefix=%s %s" % (self.cfg['preconfigopts'], tmp_mono_path, self.cfg['configopts'])
            build_cmd = ' '.join([
                "%(prebuildopts)s"
                "make %(par)s",
                "EXTERNAL_MCS=%(path)s/usr/bin/mygmcs",
                "EXTERNAL_RUNTIME=%(path)s/usr/bin/mono",
                "%(buildopts)s",
            ]) %{
                'prebuildopts': self.cfg['prebuildopts'],
                'par': par,
                'path': monorpms_path,
                'buildopts': self.cfg['buildopts'],
            }
            install_cmd = "make install"

            for cmd in [config_cmd, build_cmd, install_cmd]:
                run_cmd(cmd, log_all=True, simple=True)

            more_buildopts = ' '.join([
                "EXTERNAL_MCS=%(path)s/bin/gmcs",
                "EXTERNAL_RUNTIME=%(path)s/bin/mono",
            ]) % {'path': tmp_mono_path}
            self.cfg.update('buildopts', more_buildopts)

            self.src = self.mono_srcs

        # continue with normal configure, and subsequent make, make install
        ConfigureMake.configure_step(self)

    def sanity_check_step(self):
        """Custom sanity check for Mono."""

        binaries = ['bin/mono', 'bin/xbuild']
        if LooseVersion(self.version) >= LooseVersion('2.11'):
            binaries.append('bin/mcs')
        else:
            binaries.append('bin/gmcs')

        custom_paths = {
            'files': binaries,
            'dirs': ['include/mono-2.0/mono', 'lib'],
        }
        ConfigureMake.sanity_check_step(self, custom_paths=custom_paths)
