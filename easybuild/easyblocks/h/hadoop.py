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
EasyBuild support for building and installing Hadoop, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import glob
import os
import re
import shutil

from easybuild.easyblocks.generic.tarball import Tarball
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


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
                cmd += ' -Drequire.%s=true -D%s.prefix=%s' % (native_lib, native_lib, lib_root)

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
        """After the install, copy the extra native libraries into place."""
        for native_library, lib_path in self.cfg['extra_native_libs']:
            lib_root = get_software_root(native_library)
            lib_src = os.path.join(lib_root, lib_path)
            lib_dest = os.path.join(self.installdir, 'lib', 'native')
            self.log.info('Copying shared objects in "%s"', lib_src)
            for lib in glob.glob(lib_src):
                self.log.info('Copying "%s" to "%s"', lib, lib_dest)
                shutil.copy2(lib, lib_dest)

    def sanity_check_step(self):
        """Custom sanity check for Hadoop."""

        native_files = []
        if self.cfg['build_native_libs']:
            native_files = ['lib/native/libhadoop.%s' % get_shared_lib_ext()]

        custom_paths = {
            'files': ['bin/hadoop'] + native_files,
            'dirs': ['etc', 'libexec'],
        }
        super(EB_Hadoop, self).sanity_check_step(custom_paths=custom_paths)

        fake_mod_data = self.load_fake_module(purge=True)
        # exit code is ignored, since this cmd exits with 1 if not all native libraries were found
        cmd = "hadoop checknative -a"
        out, _ = run_cmd(cmd, simple=False, log_all=False, log_ok=False)
        self.clean_up_fake_module(fake_mod_data)

        not_found = []
        installdir = os.path.realpath(self.installdir)
        lib_src = os.path.join(installdir, 'lib', 'native')
        for native_lib, _ in self.cfg['extra_native_libs']:
            if not re.search(r'%s: *true *%s' % (native_lib, lib_src), out):
                not_found.append(native_lib)
        if not_found:
            raise EasyBuildError("%s not found by 'hadoop checknative -a'.", ', '.join(not_found))

    def make_module_extra(self):
        """Custom extra module file entries for Hadoop."""
        txt = super(EB_Hadoop, self).make_module_extra()
        mapreduce_subdir = os.path.join('share', 'hadoop', 'mapreduce')
        txt += self.module_generator.prepend_paths('HADOOP_HOME', mapreduce_subdir)
        return txt
