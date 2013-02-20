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
"""

import re
import os
import shutil

from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import run_cmd


class EB_MATLAB(EasyBlock):
    """Support for installing MATLAB."""

    configfilename = "my_installer_input.txt"

    def configure_step(self):
        """Configure MATLAB installation: create license file."""

        # create license file
        licserv = self.cfg['license_server']
        licport = self.cfg['license_server_port']
        lictxt = '\n'.join([
                            "SERVER %s 000000000000 %s" % (licserv, licport),
                            "USE_SERVER",
                           ])

        licfile = "%s/ResearchLicense.dat" % self.builddir
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

        # make sure install script is executable
        try:
            os.chmod("install", 0755)
        except OSError, err:
            self.log.error("Failed to chmod install script: %s" % err)

        configfile = "%s/%s" % (self.builddir, self.configfilename)
        cmd = 'export _JAVA_OPTIONS="-Xmx128M"; ./install -v -inputFile %s' % configfile
        run_cmd(cmd, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for MATLAB."""

        custom_paths = {
                        'files': ["bin/matlab", "bin/mcc", "bin/glnxa64/MATLAB", "bin/glnxa64/mcc",
                                  "runtime/glnxa64/libmwmclmcrrt.so"],
                        'dirs': ["java/jar", "toolbox/compiler"],
                       }

        super(EB_MATLAB, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Extend PATH and set proper _JAVA_OPTIONS (-Xmx)."""

        txt = super(EB_MATLAB, self).make_module_extra()

        txt += self.moduleGenerator.prepend_paths('PATH', ['/sbin'], allow_abs=True)
        txt += self.moduleGenerator.set_environment('_JAVA_OPTIONS', "-Xmx128M")

        return txt
