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
EasyBuild support for building and installing Hadoop, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os
import shutil

from easybuild.easyblocks.generic.tarball import Tarball
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.run import run_cmd


class EB_Hadoop(Tarball):
    """Support for building/installing Hadoop."""

    @staticmethod
    def extra_options():
        """Custom easyconfig parameters for Hadoop."""
        extra_vars = {
            'build_native_libs': [False, "Build native libraries", CUSTOM],
         }
        return Tarball.extra_options(extra_vars)

    def build_step(self):
        """Custom build procedure for Hadoop: build native libraries, if requested."""
        if self.cfg['build_native_libs']:
            cmd = "mvn package -DskipTests -Dmaven.javadoc.skip -Dtar -Pdist,native"
            if self.cfg['parallel'] > 1:
                cmd += " -T%d" % self.cfg['parallel']
            run_cmd(cmd, log_all=True, simple=True, log_ok=True)

    def install_step(self):
        """Custom install procedure for Hadoop: install-by-copy."""
        if self.cfg['build_native_libs']:
            src = os.path.join(self.cfg['start_dir'], 'hadoop-dist', 'target', 'hadoop-%s' % self.version)
            super(EB_Hadoop, self).install_step(src=src)
        else:
            super(EB_Hadoop, self).install_step()

    def sanity_check_step(self):
        """Custom sanity check for Hadoop."""
        native_files = []
        if self.cfg['build_native_libs']:
            native_files = ['lib/native/libhadoop.so']

        custom_paths = {
            'files': ['bin/hadoop'] + native_files,
            'dirs': ['etc', 'libexec'],
        }
        super(EB_Hadoop, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Custom extra module file entries for Hadoop."""
        txt = super(EB_Hadoop, self).make_module_extra()
        mapreduce_subdir = os.path.join('share', 'hadoop', 'mapreduce')
        txt += self.module_generator.prepend_paths('HADOOP_HOME', mapreduce_subdir)
        return txt
