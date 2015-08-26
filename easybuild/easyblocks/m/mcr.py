##
# Copyright 2009-2015 Ghent University
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
EasyBuild support for installing MCR, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Fotis Georgatos (Uni.Lu, NTUA)
@author: Balazs Hajgato (VUB)
"""

import re
import os
import shutil

from distutils.version import LooseVersion
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd
from easybuild.tools.filetools write_file, read_file

class EB_MCR(EasyBlock):
    """Support for installing MCR."""

    def __init__(self, *args, **kwargs):
        """Add extra config options specific to MCR."""
        super(EB_MCR, self).__init__(*args, **kwargs)
        self.comp_fam = None
        self.configfilename = "my_installer_input.txt"
        known_versions =  {'R2014a': 'v83', 'R2014b': 'v84', 'R2015a': 'v85'}
        self.extradir = known_versions.get(self.version, 'UNKNOWN')

    @staticmethod
    def extra_options():
        extra_vars = {
            'java_options': ['-Xmx256m', "$_JAVA_OPTIONS value set for install and in module file.", CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

    def configure_step(self):
        """Configure MCR installation: create license file."""

        configfile = os.path.join(self.builddir, self.configfilename)
        try:
            if LooseVersion(self.version) < LooseVersion('2015a'):
                shutil.copyfile("%s/installer_input.txt" % self.builddir, configfile)
                read_file(configfile, config)
                config = re.sub(r"^# destinationFolder=.*", "destinationFolder=%s" % self.installdir, config, re.M)
                config = re.sub(r"^# agreeToLicense=.*", "agreeToLicense=Yes", config, re.M)
                config = re.sub(r"^# mode=.*", "mode=silent", config, re.M)
            else:
                config = "destinationFolder=%s\n" % self.installdir
                config += "agreeToLicense=Yes\n"
                config += "mode=silent\n"

            write_file(configfile, config)

        except IOError, err:
            raise EasyBuildError("Failed to create installation config file %s: %s", configfile, err)

        self.log.debug('configuration file written to %s:\n %s' % (configfile, config))

    def build_step(self):
        """No building of MCR, no sources available."""
        pass

    def install_step(self):
        """MCR install procedure using 'install' command."""

        src = os.path.join(self.cfg['start_dir'], 'install')

        # make sure install script is executable
        try:
            if os.path.isfile(src):
                self.log.info("Doing chmod on source file %s" % src)
                os.chmod(src, 0755)
            else:
                self.log.info("Did not find source file %s" % src)
        except OSError, err:
            raise EasyBuildError("Failed to chmod install script: %s", err)

        # make sure $DISPLAY is not defined, which may lead to (hard to trace) problems
        # this is a workaround for not being able to specify --nodisplay to the install scripts
        if 'DISPLAY' in os.environ:
            os.environ.pop('DISPLAY')

        if not '_JAVA_OPTIONS' in self.cfg['preinstallopts']:
            self.cfg['preinstallopts'] = ('export _JAVA_OPTIONS="%s" && ' % self.cfg['java_options']) + self.cfg['preinstallopts']
        configfile = "%s/%s" % (self.builddir, self.configfilename)
        cmd = "%s ./install -v -inputFile %s %s" % (self.cfg['preinstallopts'], configfile, self.cfg['installopts'])
        run_cmd(cmd, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for MCR."""

        custom_paths = {
            'files': [''],
            'dirs': ['%s/%s/glnxa64' % (self.extradir[self.version], x) for x in ['runtime' , 'bin', 'sys/os']],
        }

        super(EB_MCR, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Extend PATH and set proper _JAVA_OPTIONS (e.g., -Xmx)."""

        extradir = self.extradir.get(self.version. 'UNKNOWN')
        txt = super(EB_MCR, self).make_module_extra()

        txt += self.module_generator.set_environment('XAPPLRESDIR', os.path.join(self.installdir, self.extradir[self.version], 'X11', 'app-defaults'))
        for ldlibdir in ['runtime', 'bin', os.path.join('sys', 'os')]:
            txt += self.module_generator.prepend_paths('LD_LIBRARY_PATH', os.path.join(self.extradir[self.version], ldlibdir, 'glnxa64'))

        txt += self.module_generator.set_environment('_JAVA_OPTIONS', self.cfg['java_options'])

        return txt
