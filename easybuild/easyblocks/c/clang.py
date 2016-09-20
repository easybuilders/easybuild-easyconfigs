##
# Copyright 2013 Dmitri Gribenko
# Copyright 2013-2016 Ghent University
#
# This file is triple-licensed under GPLv2 (see below), MIT, and
# BSD three-clause licenses.
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
Support for building and installing Clang, implemented as an easyblock.

@author: Dmitri Gribenko (National Technical University of Ukraine "KPI")
@author: Ward Poelmans (Ghent University)
"""

import fileinput
import glob
import os
import re
import shutil
import sys
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.cmakemake import CMakeMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools import run
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.config import build_option
from easybuild.tools.filetools import mkdir
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_os_name, get_os_version, get_shared_lib_ext

# List of all possible build targets for Clang
CLANG_TARGETS = ["all", "AArch64", "ARM", "CppBackend", "Hexagon", "Mips",
                 "MBlaze", "MSP430", "NVPTX", "PowerPC", "R600", "Sparc",
                 "SystemZ", "X86", "XCore"]


class EB_Clang(CMakeMake):
    """Support for bootstrapping Clang."""

    @staticmethod
    def extra_options():
        extra_vars = {
            'assertions': [True, "Enable assertions.  Helps to catch bugs in Clang.", CUSTOM],
            'build_targets': [["X86"], "Build targets for LLVM. Possible values: " + ', '.join(CLANG_TARGETS), CUSTOM],
            'bootstrap': [True, "Bootstrap Clang using GCC", CUSTOM],
            'usepolly': [False, "Build Clang with polly", CUSTOM],
            'static_analyzer': [True, "Install the static analyser of Clang", CUSTOM],
            # The sanitizer tests often fail on HPC systems due to the 'weird' environment.
            'skip_sanitizer_tests': [False, "Do not run the sanitizer tests", CUSTOM],
        }

        return CMakeMake.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Initialize custom class variables for Clang."""

        super(EB_Clang, self).__init__(*args, **kwargs)
        self.llvm_src_dir = None
        self.llvm_obj_dir_stage1 = None
        self.llvm_obj_dir_stage2 = None
        self.llvm_obj_dir_stage3 = None
        self.make_parallel_opts = ""

        unknown_targets = [target for target in self.cfg['build_targets'] if target not in CLANG_TARGETS]

        if unknown_targets:
            raise EasyBuildError("Some of the chosen build targets (%s) are not in %s.",
                                 ', '.join(unknown_targets), ', '.join(CLANG_TARGETS))

        if LooseVersion(self.version) < LooseVersion('3.4') and "R600" in self.cfg['build_targets']:
            raise EasyBuildError("Build target R600 not supported in < Clang-3.4")

        if LooseVersion(self.version) > LooseVersion('3.3') and "MBlaze" in self.cfg['build_targets']:
            raise EasyBuildError("Build target MBlaze is not supported anymore in > Clang-3.3")

    def check_readiness_step(self):
        """Fail early on RHEL 5.x and derivatives because of known bug in libc."""
        super(EB_Clang, self).check_readiness_step()
        # RHEL 5.x have a buggy libc.  Building stage 2 will fail.
        if get_os_name() in ['redhat', 'RHEL', 'centos', 'SL'] and get_os_version().startswith('5.'):
            raise EasyBuildError("Can not build Clang on %s v5.x: libc is buggy, building stage 2 will fail. "
                                 "See http://stackoverflow.com/questions/7276828/", get_os_name())

    def extract_step(self):
        """
        Prepare a combined LLVM source tree.  The layout is:
        llvm/             Unpack llvm-*.tar.gz here
          projects/
            compiler-rt/  Unpack compiler-rt-*.tar.gz here
            openmp/       Unpack openmp-*.tar.xz here
          tools/
            clang/        Unpack clang-*.tar.gz here
            polly/        Unpack polly-*.tar.gz here
        """

        # Extract everything into separate directories.
        super(EB_Clang, self).extract_step()

        # Find the full path to the directory that was unpacked from llvm-*.tar.gz.
        for tmp in self.src:
            if tmp['name'].startswith("llvm-"):
                self.llvm_src_dir = tmp['finalpath']
                break

        if self.llvm_src_dir is None:
            raise EasyBuildError("Could not determine LLVM source root (LLVM source was not unpacked?)")

        src_dirs = {}

        def find_source_dir(globpatterns, targetdir):
            """Search for directory with globpattern and rename it to targetdir"""
            if not isinstance(globpatterns, list):
                globpatterns = [globpatterns]

            glob_src_dirs = [glob_dir for globpattern in globpatterns for glob_dir in glob.glob(globpattern)]
            if len(glob_src_dirs) != 1:
                raise EasyBuildError("Failed to find exactly one source directory for pattern %s: %s", globpatterns,
                                     glob_src_dirs)
            src_dirs[glob_src_dirs[0]] = targetdir

        find_source_dir('compiler-rt-*', os.path.join(self.llvm_src_dir, 'projects', 'compiler-rt'))

        if self.cfg["usepolly"]:
            find_source_dir('polly-*', os.path.join(self.llvm_src_dir, 'tools', 'polly'))

        find_source_dir(['clang-*', 'cfe-*'], os.path.join(self.llvm_src_dir, 'tools', 'clang'))

        if LooseVersion(self.version) >= LooseVersion('3.8'):
            find_source_dir('openmp-*', os.path.join(self.llvm_src_dir, 'projects', 'openmp'))

        for src in self.src:
            for (dirname, new_path) in src_dirs.items():
                if src['name'].startswith(dirname):
                    old_path = os.path.join(src['finalpath'], dirname)
                    try:
                        shutil.move(old_path, new_path)
                    except IOError, err:
                        raise EasyBuildError("Failed to move %s to %s: %s", old_path, new_path, err)
                    src['finalpath'] = new_path
                    break

    def configure_step(self):
        """Run CMake for stage 1 Clang."""

        self.llvm_obj_dir_stage1 = os.path.join(self.builddir, 'llvm.obj.1')
        if self.cfg['bootstrap']:
            self.llvm_obj_dir_stage2 = os.path.join(self.builddir, 'llvm.obj.2')
            self.llvm_obj_dir_stage3 = os.path.join(self.builddir, 'llvm.obj.3')

        if LooseVersion(self.version) >= LooseVersion('3.3'):
            disable_san_tests = False
            # all sanitizer tests will fail when there's a limit on the vmem
            # this is ugly but I haven't found a cleaner way so far
            (vmemlim, ec) = run_cmd("ulimit -v", regexp=False)
            if not vmemlim.startswith("unlimited"):
                disable_san_tests = True
                self.log.warn("There is a virtual memory limit set of %s KB. The tests of the "
                              "sanitizers will be disabled as they need unlimited virtual "
                              "memory unless --strict=error is used." % vmemlim.strip())

            # the same goes for unlimited stacksize
            (stacklim, ec) = run_cmd("ulimit -s", regexp=False)
            if stacklim.startswith("unlimited"):
                disable_san_tests = True
                self.log.warn("The stacksize limit is set to unlimited. This causes the ThreadSanitizer "
                              "to fail. The sanitizers tests will be disabled unless --strict=error is used.")

            if (disable_san_tests or self.cfg['skip_sanitizer_tests']) and build_option('strict') != run.ERROR:
                self.log.debug("Disabling the sanitizer tests")
                self.disable_sanitizer_tests()

        # Create and enter build directory.
        mkdir(self.llvm_obj_dir_stage1)
        os.chdir(self.llvm_obj_dir_stage1)

        # GCC and Clang are installed in different prefixes and Clang will not
        # find the GCC installation on its own.
        self.cfg['configopts'] += "-DGCC_INSTALL_PREFIX='%s' " % get_software_root('GCC')

        self.cfg['configopts'] += "-DCMAKE_BUILD_TYPE=Release "
        if self.cfg['assertions']:
            self.cfg['configopts'] += "-DLLVM_ENABLE_ASSERTIONS=ON "
        else:
            self.cfg['configopts'] += "-DLLVM_ENABLE_ASSERTIONS=OFF "

        self.cfg['configopts'] += '-DLLVM_TARGETS_TO_BUILD="%s" ' % ';'.join(self.cfg['build_targets'])

        if self.cfg['parallel']:
            self.make_parallel_opts = "-j %s" % self.cfg['parallel']

        self.log.info("Configuring")
        super(EB_Clang, self).configure_step(srcdir=self.llvm_src_dir)

    def disable_sanitizer_tests(self):
        """Disable the tests of all the sanitizers by removing the test directories from the build system"""
        if LooseVersion(self.version) < LooseVersion('3.6'):
            # for Clang 3.5 and lower, the tests are scattered over several CMakeLists.
            # We loop over them, and patch out the rule that adds the sanitizers tests to the testsuite
            patchfiles = [
                "lib/asan",
                "lib/dfsan",
                "lib/lsan",
                "lib/msan",
                "lib/tsan",
                "lib/ubsan",
            ]

            for patchfile in patchfiles:
                patchfile_fp = os.path.join(self.llvm_src_dir, "projects/compiler-rt", patchfile, "CMakeLists.txt")
                if os.path.exists(patchfile_fp):
                    self.log.debug("Patching %s in %s" % (patchfile, self.llvm_src_dir))
                    try:
                        for line in fileinput.input(patchfile_fp, inplace=1, backup='.orig'):
                            if "add_subdirectory(lit_tests)" not in line:
                                sys.stdout.write(line)
                    except (IOError, OSError), err:
                        raise EasyBuildError("Failed to patch %s: %s", patchfile_fp, err)
                else:
                    self.log.debug("Not patching non-existent %s in %s" % (patchfile, self.llvm_src_dir))

            # There is a common part seperate for the specific saniters, we disable all
            # the common tests
            patchfile = "projects/compiler-rt/lib/sanitizer_common/CMakeLists.txt"
            try:
                for line in fileinput.input("%s/%s" % (self.llvm_src_dir, patchfile), inplace=1, backup='.orig'):
                    if "add_subdirectory(tests)" not in line:
                        sys.stdout.write(line)
            except IOError, err:
                raise EasyBuildError("Failed to patch %s/%s: %s", self.llvm_src_dir, patchfile, err)
        else:
            # In Clang 3.6, the sanitizer tests are grouped together in one CMakeLists
            # We patch out adding the subdirectories with the sanitizer tests
            patchfile = "projects/compiler-rt/test/CMakeLists.txt"
            patchfile_fp = os.path.join(self.llvm_src_dir, patchfile)
            self.log.debug("Patching %s in %s" % (patchfile, self.llvm_src_dir))
            patch_regex = re.compile(r'add_subdirectory\((.*san|sanitizer_common)\)')
            try:
                for line in fileinput.input(patchfile_fp, inplace=1, backup='.orig'):
                    if not patch_regex.search(line):
                        sys.stdout.write(line)
            except IOError, err:
                raise EasyBuildError("Failed to patch %s: %s", patchfile_fp, err)

    def build_with_prev_stage(self, prev_obj, next_obj):
        """Build Clang stage N using Clang stage N-1"""

        # Create and enter build directory.
        mkdir(next_obj)
        os.chdir(next_obj)

        # Configure.
        CC = os.path.join(prev_obj, 'bin', 'clang')
        CXX = os.path.join(prev_obj, 'bin', 'clang++')

        options = "-DCMAKE_INSTALL_PREFIX=%s " % self.installdir
        options += "-DCMAKE_C_COMPILER='%s' " % CC
        options += "-DCMAKE_CXX_COMPILER='%s' " % CXX
        options += self.cfg['configopts']

        self.log.info("Configuring")
        run_cmd("cmake %s %s" % (options, self.llvm_src_dir), log_all=True)

        self.log.info("Building")
        run_cmd("make %s" % self.make_parallel_opts, log_all=True)

    def run_clang_tests(self, obj_dir):
        os.chdir(obj_dir)

        self.log.info("Running tests")
        run_cmd("make %s check-all" % self.make_parallel_opts, log_all=True)

    def build_step(self):
        """Build Clang stage 1, 2, 3"""

        # Stage 1: build using system compiler.
        self.log.info("Building stage 1")
        os.chdir(self.llvm_obj_dir_stage1)
        super(EB_Clang, self).build_step()

        if self.cfg['bootstrap']:
            # Stage 1: run tests.
            self.run_clang_tests(self.llvm_obj_dir_stage1)

            self.log.info("Building stage 2")
            self.build_with_prev_stage(self.llvm_obj_dir_stage1, self.llvm_obj_dir_stage2)
            self.run_clang_tests(self.llvm_obj_dir_stage2)

            self.log.info("Building stage 3")
            self.build_with_prev_stage(self.llvm_obj_dir_stage2, self.llvm_obj_dir_stage3)
            # Don't run stage 3 tests here, do it in the test step.

    def test_step(self):
        if self.cfg['bootstrap']:
            self.run_clang_tests(self.llvm_obj_dir_stage3)
        else:
            self.run_clang_tests(self.llvm_obj_dir_stage1)

    def install_step(self):
        """Install stage 3 binaries."""

        if self.cfg['bootstrap']:
            os.chdir(self.llvm_obj_dir_stage3)
        else:
            os.chdir(self.llvm_obj_dir_stage1)
        super(EB_Clang, self).install_step()

        # the static analyzer is not installed by default
        # we do it by hand
        if self.cfg['static_analyzer'] and LooseVersion(self.version) < LooseVersion('3.8'):
            try:
                tools_src_dir = os.path.join(self.llvm_src_dir, 'tools', 'clang', 'tools')
                analyzer_target_dir = os.path.join(self.installdir, 'libexec', 'clang-analyzer')
                bindir = os.path.join(self.installdir, 'bin')
                for scan_dir in ['scan-build', 'scan-view']:
                    shutil.copytree(os.path.join(tools_src_dir, scan_dir), os.path.join(analyzer_target_dir, scan_dir))
                    os.symlink(os.path.relpath(bindir, os.path.join(analyzer_target_dir, scan_dir)),
                               os.path.join(analyzer_target_dir, scan_dir, 'bin'))
                    os.symlink(os.path.relpath(os.path.join(analyzer_target_dir, scan_dir, scan_dir), bindir),
                               os.path.join(bindir, scan_dir))

                mandir = os.path.join(self.installdir, 'share', 'man', 'man1')
                os.makedirs(mandir)
                shutil.copy2(os.path.join(tools_src_dir, 'scan-build', 'scan-build.1'), mandir)
            except OSError, err:
                raise EasyBuildError("Failed to copy static analyzer dirs to install dir: %s", err)

    def sanity_check_step(self):
        """Custom sanity check for Clang."""
        shlib_ext = get_shared_lib_ext()
        custom_paths = {
            'files': [
                "bin/clang", "bin/clang++", "bin/llvm-ar", "bin/llvm-nm", "bin/llvm-as", "bin/opt", "bin/llvm-link",
                "bin/llvm-config", "bin/llvm-symbolizer", "include/llvm-c/Core.h", "include/clang-c/Index.h",
                "lib/libclang.%s" % shlib_ext, "lib/clang/%s/include/stddef.h" % self.version,
            ],
            'dirs': ["include/clang", "include/llvm", "lib/clang/%s/lib" % self.version],
        }
        if self.cfg['static_analyzer']:
            custom_paths['files'].extend(["bin/scan-build", "bin/scan-view"])

        if self.cfg["usepolly"]:
            custom_paths['files'].extend(["lib/LLVMPolly.%s" % shlib_ext])
            custom_paths['dirs'].extend(["include/polly"])

        if LooseVersion(self.version) >= LooseVersion('3.8'):
            custom_paths['files'].extend(["lib/libomp.%s" % shlib_ext, "lib/clang/%s/include/omp.h" % self.version])

        super(EB_Clang, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Custom variables for Clang module."""
        txt = super(EB_Clang, self).make_module_extra()
        # we set the symbolizer path so that asan/tsan give meanfull output by default
        asan_symbolizer_path = os.path.join(self.installdir, 'bin', 'llvm-symbolizer')
        txt += self.module_generator.set_environment('ASAN_SYMBOLIZER_PATH', asan_symbolizer_path)
        return txt
