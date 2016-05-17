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
EasyBuild support for installing MCR, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Fotis Georgatos (Uni.Lu, NTUA)
@author: Balazs Hajgato (Vrije Universiteit Brussel)
"""
import re
import os
import shutil
import stat

from distutils.version import LooseVersion
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import adjust_permissions, read_file, write_file
from easybuild.tools.run import run_cmd


class EB_MCR(EasyBlock):
    """Support for installing MCR."""

    def __init__(self, *args, **kwargs):
        """Add extra config options specific to MCR."""
        super(EB_MCR, self).__init__(*args, **kwargs)
        self.comp_fam = None
        self.configfilename = "my_installer_input.txt"
        self.subdir = ''

    @staticmethod
    def extra_options():
        """Custom easyconfig parameters for MCR."""
        extra_vars = {
            'java_options': ['-Xmx256m', "$_JAVA_OPTIONS value set for install and in module file.", CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

    def configure_step(self):
        """Configure MCR installation: create license file."""

        configfile = os.path.join(self.builddir, self.configfilename)
        if LooseVersion(self.version) < LooseVersion('2015a'):
            shutil.copyfile(os.path.join(self.cfg['start_dir'], 'installer_input.txt'), configfile)
            config = read_file(configfile)
            config = re.sub(r"^# destinationFolder=.*", "destinationFolder=%s" % self.installdir, config, re.M)
            config = re.sub(r"^# agreeToLicense=.*", "agreeToLicense=Yes", config, re.M)
            config = re.sub(r"^# mode=.*", "mode=silent", config, re.M)
        else:
            config = '\n'.join([
                "destinationFolder=%s" % self.installdir,
                "agreeToLicense=Yes",
                "mode=silent",
            ])

        write_file(configfile, config)

        self.log.debug("configuration file written to %s:\n %s", configfile, config)

    def build_step(self):
        """No building of MCR, no sources available."""
        pass

    def install_step(self):
        """MCR install procedure using 'install' command."""

        src = os.path.join(self.cfg['start_dir'], 'install')

        # make sure install script is executable
        adjust_permissions(src, stat.S_IXUSR)

        # make sure $DISPLAY is not defined, which may lead to (hard to trace) problems
        # this is a workaround for not being able to specify --nodisplay to the install scripts
        if 'DISPLAY' in os.environ:
            os.environ.pop('DISPLAY')

        if not '_JAVA_OPTIONS' in self.cfg['preinstallopts']:
            java_options = 'export _JAVA_OPTIONS="%s" && ' % self.cfg['java_options']
            self.cfg['preinstallopts'] = java_options + self.cfg['preinstallopts']

        configfile = "%s/%s" % (self.builddir, self.configfilename)
        cmd = "%s ./install -v -inputFile %s %s" % (self.cfg['preinstallopts'], configfile, self.cfg['installopts'])
        run_cmd(cmd, log_all=True, simple=True)

        # determine subdirectory (e.g. v84 (2014a, 2014b), v85 (2015a), ...)
        subdirs = os.listdir(self.installdir)
        if len(subdirs) == 1:
            self.subdir = subdirs[0]
        else:
            raise EasyBuildError("Found multiple subdirectories, don't know which one to pick: %s", subdirs)

    def sanity_check_step(self):
        """Custom sanity check for MCR."""
        custom_paths = {
            'files': [],
            'dirs': [os.path.join(self.subdir, x, 'glnxa64') for x in ['runtime', 'bin', 'sys/os']],
        }
        super(EB_MCR, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Extend PATH and set proper _JAVA_OPTIONS (e.g., -Xmx)."""
        txt = super(EB_MCR, self).make_module_extra()

        xapplresdir = os.path.join(self.installdir, self.subdir, 'X11', 'app-defaults')
        txt += self.module_generator.set_environment('XAPPLRESDIR', xapplresdir)
        for ldlibdir in ['runtime', 'bin', os.path.join('sys', 'os')]:
            libdir = os.path.join(self.subdir, ldlibdir, 'glnxa64')
            txt += self.module_generator.prepend_paths('LD_LIBRARY_PATH', libdir)

        txt += self.module_generator.set_environment('_JAVA_OPTIONS', self.cfg['java_options'])
        txt += self.module_generator.set_environment('MCRROOT', os.path.join(self.installdir, self.subdir))

        return txt
