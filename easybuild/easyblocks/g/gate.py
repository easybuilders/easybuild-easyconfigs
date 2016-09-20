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
EasyBuild support for building and installing Gate, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Toon Willems (Ghent University)
"""
import os
import shutil
from distutils.version import LooseVersion

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.cmakemake import CMakeMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_GATE(CMakeMake):
    """Support for building/installing GATE."""

    @staticmethod
    def extra_options():
        extra_vars = {
            'default_platform': ['openPBS', "Default cluster platform to set", CUSTOM],
        }
        return CMakeMake.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Initialise class variables."""
        super(EB_GATE, self).__init__(*args, **kwargs)
        self.g4system = None
        self.gate_subdirs = [
            '.',
            os.path.join('cluster_tools', 'filemerger'),
            os.path.join('cluster_tools', 'jobsplitter'),
        ]

    def configure_step(self):
        """Custom configure procedure for GATE: CMake for versions 6.2 or more recent."""

        if LooseVersion(self.version) >= '6.2':
            super(EB_GATE, self).configure_step()

    def build_step(self):
        """Custom build procedure for GATE, including cluster tools."""

        if LooseVersion(self.version) < '6.2':
            # build procedure for versions older than v6.2: source env_gate.sh and run 'make'
            env_gate_script = os.path.join(self.cfg['start_dir'], 'env_gate.sh')
            self.cfg['prebuildopts'] = "source %s && %s " % (env_gate_script, self.cfg['prebuildopts'])

        if LooseVersion(self.version) <= '6.2':
            if self.toolchain.comp_family() in [toolchain.INTELCOMP]:
                # include missing library path in linker command
                self.cfg.update('buildopts', 'LD="$CXX -L$EBROOTICC/compiler/lib/intel64"')

        # redefine $CFLAGS/$CXXFLAGS via options to build command ('make')
        cflags = os.getenv('CFLAGS')
        cxxflags = "%s -DGC_DEFAULT_PLATFORM=\\'%s\\'" % (os.getenv('CXXFLAGS'), self.cfg['default_platform'])
        if self.toolchain.comp_family() in [toolchain.INTELCOMP]:
            # make sure GNU macros are defined by Intel compiler
            cflags += " -gcc"
            cxxflags += " -gcc"

        # make sure right compilers and compiler options are used for building
        make_opts = {
            'CC': os.getenv('CC'),
            'CFLAGS': cflags,
            'CXX': os.getenv('CXX'),
            'CXXFLAGS': cxxflags,
            # filemerger Makefile hardcodes $LD to g++, so make sure right compiler is used for linking
            'LD': os.getenv('CXX'),
        }
        for key in sorted(make_opts):
            self.cfg.update('buildopts', '%s="%s"' % (key, make_opts[key]))

        for subdir in self.gate_subdirs:
            try:
                os.chdir(os.path.join(os.path.join(self.cfg['start_dir'], subdir)))
            except OSError, err:
                raise EasyBuildError("Failed to move to %s: %s", subdir, err)

            super(EB_GATE, self).build_step()

        try:
            os.chdir(self.cfg['start_dir'])
        except OSError, err:
            raise EasyBuildError("Failed to return to start dir %s: %s", self.cfg['start_dir'], err)

    def install_step(self):
        """Custom installation procedure for GATE."""

        if LooseVersion(self.version) >= '6.2':
            # make sure installation prefix is honored (for cluster tools, requires Makefile patch)
            self.cfg.update('installopts', 'PREFIX=%(installdir)s')

            for subdir in self.gate_subdirs:
                try:
                    os.chdir(os.path.join(os.path.join(self.cfg['start_dir'], subdir)))
                except OSError, err:
                    raise EasyBuildError("Failed to move to %s: %s", subdir, err)

                super(EB_GATE, self).install_step()
        else:
            # manually copy files for versions prior to v6.2

            # copy all the things
            try:
                shutil.rmtree(self.installdir)
                shutil.copytree(self.cfg['start_dir'], self.installdir)
            except OSError, err:
                raise EasyBuildError("Failed to copy %s to %s: %s", self.cfg['start_dir'], self.installdir, err)

            cmd = "source %s &> /dev/null && echo $G4SYSTEM" % os.path.join(self.cfg['start_dir'], 'env_gate.sh')
            out, _ = run_cmd(cmd, simple=False)
            self.g4system = out.strip()
            if self.g4system:
                self.log.debug("Value obtained for $G4SYSTEM: %s" % self.g4system)
            else:
                raise EasyBuildError("Failed to obtain value for $G4SYSTEM, not set?")

            # copy Gate libraries to 'lib' subdir in installation directory
            try:
                shlib_ext = get_shared_lib_ext()
                libdir = os.path.join(self.installdir, "lib")
                os.mkdir(libdir)
                srclibdir = os.path.join(self.cfg['start_dir'], "tmp", self.g4system, "Gate")
                for fil in os.listdir(srclibdir):
                    if fil.endswith('.%s' % shlib_ext):
                        shutil.copy2(os.path.join(srclibdir, fil), os.path.join(libdir, fil))
                        self.log.debug("Copied library %s to 'lib' install subdirectory" % fil)
            except OSError, err:
                raise EasyBuildError("Failed to copy GATE library/ies to lib directory: %s", err)

            # add link from tmp/<OS>-<comp>/gjs to lib
            js_dir = os.path.join(self.installdir, 'cluster_tools', 'jobsplitter')
            try:
                os.symlink(os.path.join(js_dir, 'tmp', self.g4system, 'gjs'), os.path.join(js_dir, 'lib'))
            except OSError, err:
                raise EasyBuildError("Failed to symlink tmp js dir to lib in %s: %s", js_dir, err)

    def make_module_extra(self):
        """Overwritten from Application to add extra txt"""
        subdir = os.getenv('G4SYSTEM', '')
        txt = super(EB_GATE, self).make_module_extra()
        path_dirs = []
        fm_bin = os.path.join('cluster_tools', 'filemerger', 'bin', subdir)
        js_dir = os.path.join('cluster_tools', 'jobsplitter')
        js_bin = os.path.join(js_dir, 'bin', subdir)
        for path_dir in [os.path.join('bin', subdir), fm_bin, js_bin]:
            if os.path.exists(os.path.join(self.installdir, path_dir)):
                path_dirs.append(path_dir)
        txt += self.module_generator.prepend_paths('PATH', path_dirs)
        txt += self.module_generator.prepend_paths('LD_LIBRARY_PATH', [os.path.join(js_dir, 'lib')])
        txt += self.module_generator.set_environment('GATEHOME', self.installdir)
        txt += self.module_generator.set_environment('GC_GATE_EXE_DIR', os.path.join(self.installdir, 'bin', subdir))
        return txt

    def sanity_check_step(self):
        """Custom sanity check for GATE."""

        if LooseVersion(self.version) >= '6.2':
            subdir = ''
            extra_files = ["bin/gjm", "bin/gjs"]
            dirs = []
            if LooseVersion(self.version) < '7.0':
                extra_files += ["Utilities/itkzlib/%s" % x for x in ['itk_zlib_mangle.h', 'zconf.h',
                                                                    'zlibDllConfig.h', 'zlib.h']]
                extra_files += ["Utilities/MetaIO/%s" % x for x in ['localMetaConfiguration.h', 'metaDTITube.h',
                                                                    'metaImage.h', 'metaMesh.h', 'metaTubeGraph.h',
                                                                    'metaUtils.h']]
        else:
            subdir = self.g4system
            extra_files = [
                os.path.join('cluster_tools', 'filemerger', 'bin', subdir, 'gjm'),
                os.path.join('cluster_tools', 'jobsplitter', 'bin', subdir, 'gjs'),
                'lib/libGate.%s' % get_shared_lib_ext(),
            ]
            dirs = ['benchmarks', 'examples']

        custom_paths = {
            'files': [os.path.join('bin', subdir, 'Gate')] + extra_files,
            'dirs' : dirs,
        }
        super(EB_GATE, self).sanity_check_step(custom_paths=custom_paths)
