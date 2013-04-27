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
EasyBuild support for installing MATLAB, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Fotis Georgatos (University of Luxembourg)
"""

import re
import os
import shutil

from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import run_cmd


class EB_MATLAB(EasyBlock):
    """Support for installing MATLAB."""

    def __init__(self, *args, **kwargs):
        """Add extra config options specific to MATLAB."""
        super(EB_MATLAB, self).__init__(*args, **kwargs)
        self.comp_fam = None
        self.configfilename = "my_installer_input.txt"

    @staticmethod
    def extra_options():
        extra_vars = [
                      ('java_options', ['-Xmx256m', "$_JAVA_OPTIONS value set for install and in module file.", CUSTOM]),
                     ]
        return EasyBlock.extra_options(extra_vars)

    def configure_step(self):
        """Configure MATLAB installation: create license file."""

        # create license file
        licserv = self.cfg['license_server']
        licport = self.cfg['license_server_port']
        lictxt = '\n'.join([
                            "SERVER %s 000000000000 %s" % (licserv, licport),
                            "USE_SERVER",
                           ])

        licfile = "%s/matlab.lic" % self.builddir
        try:
            f = file(licfile, "w")
            f.write(lictxt)
            f.close()
        except IOError, err:
            self.log.error("Failed to create license file %s: %s" % (licfile, err))

        configfile = os.path.join(self.builddir, self.configfilename)
        try:
            shutil.copyfile("%s/%s/installer_input.txt" % (self.builddir, self.version), configfile)
            config = file(configfile).read()

            regdest = re.compile(r"^# destinationFolder=.*", re.M)
            regkey = re.compile(r"^# fileInstallationKey=.*", re.M)
            regagree = re.compile(r"^# agreeToLicense=.*", re.M)
            regmode = re.compile(r"^# mode=.*", re.M)
            reglicpath = re.compile(r"^# licensePath=.*", re.M)

            config = regdest.sub("destinationFolder=%s" % self.installdir, config)
            key = self.cfg['key']
            config = regkey.sub("fileInstallationKey=%s" % key, config)
            config = regagree.sub("agreeToLicense=Yes", config)
            config = regmode.sub("mode=silent", config)
            config = reglicpath.sub("licensePath=%s" % licfile, config)

            f = open(configfile, 'w')
            f.write(config)
            f.close()

        except IOError, err:
            self.log.error("Failed to create installation config file %s: %s" % (configfile, err))

        self.log.debug('configuration file written to %s:\n %s' % (configfile, config))

    def build_step(self):
        """No building of MATLAB, no sources available."""
        pass

    def install_step(self):
        """MATLAB install procedure using 'install' command."""

        src = os.path.join(self.cfg['start_dir'], 'install')

        # make sure install script is executable
        try:
            if os.path.isfile(src):
                self.log.info("Doing chmod on source file %s" % src)
                os.chmod(src, 0755)
            else:
                self.log.info("Did not find source file %s" % src)
        except OSError, err:
            self.log.error("Failed to chmod install script: %s" % err)

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
        """Custom sanity check for MATLAB."""

        custom_paths = {
                        'files': ["bin/matlab", "bin/mcc", "bin/glnxa64/MATLAB", "bin/glnxa64/mcc",
                                  "runtime/glnxa64/libmwmclmcrrt.so", "toolbox/local/classpath.txt"],
                        'dirs': ["java/jar", "toolbox/compiler"],
                       }

        super(EB_MATLAB, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Extend PATH and set proper _JAVA_OPTIONS (e.g., -Xmx)."""

        txt = super(EB_MATLAB, self).make_module_extra()

        txt += self.moduleGenerator.set_environment('_JAVA_OPTIONS', self.cfg['java_options'])

        return txt

