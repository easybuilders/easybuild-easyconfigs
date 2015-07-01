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
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd


class EB_Hadoop(Tarball):
    """Support for building/installing Hadoop."""

    @staticmethod
    def extra_options():
        """Custom easyconfig parameters for Hadoop."""
        extra_vars = {
            'build_native_libs': [False, "Build native libraries", CUSTOM],
            'extra_native_libs': [[], "Extra native libraries to install (list of tuples)", CUSTOM],
         }
        return Tarball.extra_options(extra_vars)

    def build_step(self):
        """Custom build procedure for Hadoop: build native libraries, if requested."""
        if self.cfg['build_native_libs']:
            cmd = "mvn package -DskipTests -Dmaven.javadoc.skip -Dtar -Pdist,native"

            # Building snappy, bzip2 jars w/ native libs requires -Drequire.snappy -Drequire.bzip2, etc.
            for native_lib, lib_path in self.cfg['extra_native_libs']:
                lib_root = get_software_root(native_lib)
                if not lib_root:
                    raise EasyBuildError("%s not found. Failing install" % native_lib)
                cmd += ' -Drequire.%s=true' % native_lib

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

    def post_install_step(self):
        """After the install, copy libsnappy into place."""
        for native_library, lib_path in self.cfg['extra_native_libs']:
            lib_root = get_software_root(native_library)
            lib_src = os.path.join(lib_root, lib_path)
            lib_dest = os.path.join(self.installdir, 'lib')
            shutil.copytree(lib_src, lib_dest)

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
