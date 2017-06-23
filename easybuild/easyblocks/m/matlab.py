##
# Copyright 2009-2017 Ghent University
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
EasyBuild support for installing MATLAB, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Fotis Georgatos (Uni.Lu, NTUA)
"""
import re
import os
import shutil
import stat

from distutils.version import LooseVersion

from easybuild.easyblocks.generic.packedbinary import PackedBinary
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import adjust_permissions, change_dir, read_file, write_file
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_MATLAB(PackedBinary):
    """Support for installing MATLAB."""

    def __init__(self, *args, **kwargs):
        """Add extra config options specific to MATLAB."""
        super(EB_MATLAB, self).__init__(*args, **kwargs)
        self.comp_fam = None
        self.configfile = os.path.join(self.builddir, 'my_installer_input.txt')

    @staticmethod
    def extra_options():
        extra_vars = {
            'java_options': ['-Xmx256m', "$_JAVA_OPTIONS value set for install and in module file.", CUSTOM],
        }
        return PackedBinary.extra_options(extra_vars)

    def configure_step(self):
        """Configure MATLAB installation: create license file."""

        licserv = self.cfg['license_server']
        if licserv is None:
            licserv = os.getenv('EB_MATLAB_LICENSE_SERVER', 'license.example.com')
        licport = self.cfg['license_server_port']
        if licport is None:
            licport = os.getenv('EB_MATLAB_LICENSE_SERVER_PORT', '00000')

        key = self.cfg['key']
        if key is None:
            key = os.getenv('EB_MATLAB_KEY', '00000-00000-00000-00000-00000-00000-00000-00000-00000-00000')

        # create license file
        lictxt = '\n'.join([
            "SERVER %s 000000000000 %s" % (licserv, licport),
            "USE_SERVER",
        ])

        licfile = os.path.join(self.builddir, 'matlab.lic')
        write_file(licfile, lictxt)

        try:
            shutil.copyfile(os.path.join(self.cfg['start_dir'], 'installer_input.txt'), self.configfile)
            config = read_file(self.configfile)

            regdest = re.compile(r"^# destinationFolder=.*", re.M)
            regkey = re.compile(r"^# fileInstallationKey=.*", re.M)
            regagree = re.compile(r"^# agreeToLicense=.*", re.M)
            regmode = re.compile(r"^# mode=.*", re.M)
            reglicpath = re.compile(r"^# licensePath=.*", re.M)

            config = regdest.sub("destinationFolder=%s" % self.installdir, config)
            config = regkey.sub("fileInstallationKey=%s" % key, config)
            config = regagree.sub("agreeToLicense=Yes", config)
            config = regmode.sub("mode=silent", config)
            config = reglicpath.sub("licensePath=%s" % licfile, config)

            write_file(self.configfile, config)

        except IOError, err:
            raise EasyBuildError("Failed to create installation config file %s: %s", self.configfile, err)

        self.log.debug('configuration file written to %s:\n %s', self.configfile, config)

    def install_step(self):
        """MATLAB install procedure using 'install' command."""

        src = os.path.join(self.cfg['start_dir'], 'install')

        # make sure install script is executable
        adjust_permissions(src, stat.S_IXUSR)

        if LooseVersion(self.version) >= LooseVersion('2016b'):
            jdir = os.path.join(self.cfg['start_dir'], 'sys', 'java', 'jre', 'glnxa64', 'jre', 'bin')
            for perm_dir in [os.path.join(self.cfg['start_dir'], 'bin', 'glnxa64'), jdir]:
                adjust_permissions(perm_dir, stat.S_IXUSR)

        # make sure $DISPLAY is not defined, which may lead to (hard to trace) problems
        # this is a workaround for not being able to specify --nodisplay to the install scripts
        if 'DISPLAY' in os.environ:
            os.environ.pop('DISPLAY')

        if not '_JAVA_OPTIONS' in self.cfg['preinstallopts']:
            self.cfg['preinstallopts'] = ('export _JAVA_OPTIONS="%s" && ' % self.cfg['java_options']) + self.cfg['preinstallopts']
        if LooseVersion(self.version) >= LooseVersion('2016b'):
            change_dir(self.builddir)

        cmd = "%s %s -v -inputFile %s %s" % (self.cfg['preinstallopts'], src, self.configfile, self.cfg['installopts'])
        run_cmd(cmd, log_all=True, simple=True)

    def sanity_check_step(self):
        """Custom sanity check for MATLAB."""
        custom_paths = {
            'files': ["bin/matlab", "bin/mcc", "bin/glnxa64/MATLAB", "bin/glnxa64/mcc",
                      "runtime/glnxa64/libmwmclmcrrt.%s" % get_shared_lib_ext(), "toolbox/local/classpath.txt"],
            'dirs': ["java/jar", "toolbox/compiler"],
        }
        super(EB_MATLAB, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Extend PATH and set proper _JAVA_OPTIONS (e.g., -Xmx)."""
        txt = super(EB_MATLAB, self).make_module_extra()
        txt += self.module_generator.set_environment('_JAVA_OPTIONS', self.cfg['java_options'])
        return txt
