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
EasyBuild support for building and installing GCC, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Toon Willems (Ghent University)
@author: Ward Poelmans (Ghent University)
"""

import os
import re
import shutil
from copy import copy
from distutils.version import LooseVersion
from vsc.utils.missing import any

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import check_os_dependency, get_os_name, get_os_type, get_shared_lib_ext, get_platform_name


class EB_GCC(ConfigureMake):
    """
    Self-contained build of GCC.
    Uses system compiler for initial build, then bootstraps.
    """

    @staticmethod
    def extra_options():
        extra_vars = {
            'languages': [[], "List of languages to build GCC for (--enable-languages)", CUSTOM],
            'withlto': [True, "Enable LTO support", CUSTOM],
            'withcloog': [False, "Build GCC with CLooG support", CUSTOM],
            'withppl': [False, "Build GCC with PPL support", CUSTOM],
            'withisl': [False, "Build GCC with ISL support", CUSTOM],
            'pplwatchdog': [False, "Enable PPL watchdog", CUSTOM],
            'clooguseisl': [False, "Use ISL with CLooG or not", CUSTOM],
            'multilib': [False, "Build multilib gcc (both i386 and x86_64)", CUSTOM],
        }
        return ConfigureMake.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        super(EB_GCC, self).__init__(*args, **kwargs)

        self.stagedbuild = False

        if LooseVersion(self.version) >= LooseVersion("4.8.0") and self.cfg['clooguseisl'] and not self.cfg['withisl']:
            raise EasyBuildError("Using ISL bundled with CLooG is unsupported in >=GCC-4.8.0. "
                                 "Use a seperate ISL: set withisl=True")

        # I think ISL without CLooG has no purpose in GCC < 5.0.0 ...
        if LooseVersion(self.version) < LooseVersion("5.0.0") and self.cfg['withisl'] and not self.cfg['withcloog']:
            raise EasyBuildError("Activating ISL without CLooG is pointless")

        # unset some environment variables that are known to may cause nasty build errors when bootstrapping
        self.cfg.update('unwanted_env_vars', ['CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'OBJC_INCLUDE_PATH'])
        # ubuntu needs the LIBRARY_PATH env var to work apparently (#363)
        if get_os_name() not in ['ubuntu', 'debian']:
            self.cfg.update('unwanted_env_vars', ['LIBRARY_PATH'])

        self.platform_lib = get_platform_name(withversion=True)

    def create_dir(self, dirname):
        """
        Create a dir to build in.
        """
        dirpath = os.path.join(self.cfg['start_dir'], dirname)
        try:
            os.mkdir(dirpath)
            os.chdir(dirpath)
            self.log.debug("Created dir at %s" % dirpath)
            return dirpath
        except OSError, err:
            raise EasyBuildError("Can't use dir %s to build in: %s", dirpath, err)

    def prep_extra_src_dirs(self, stage, target_prefix=None):
        """
        Prepare extra (optional) source directories, so GCC will build these as well.
        """
        if LooseVersion(self.version) >= LooseVersion('4.5'):
            known_stages = ["stage1", "stage2", "stage3"]
            if stage not in known_stages:
                raise EasyBuildError("Incorrect argument for prep_extra_src_dirs, should be one of: %s", known_stages)

            configopts = ''
            if stage == "stage2":
                # no MPFR/MPC needed in stage 2
                extra_src_dirs = ["gmp"]
            else:
                extra_src_dirs = ["gmp", "mpfr", "mpc"]

            # list of the extra dirs that are needed depending on the 'with%s' option
            # the order is important: keep CLooG last!
            self.with_dirs = ["isl", "ppl", "cloog"]

            # add optional ones that were selected (e.g. CLooG, PPL, ...)
            for x in self.with_dirs:
                if self.cfg['with%s' % x]:
                    extra_src_dirs.append(x)

            # see if modules are loaded
            # if module is available, just use the --with-X GCC configure option
            for extra in copy(extra_src_dirs):
                envvar = get_software_root(extra)
                if envvar:
                    configopts += " --with-%s=%s" % (extra, envvar)
                    extra_src_dirs.remove(extra)
                elif extra in self.with_dirs and stage in ["stage1", "stage3"]:
                    # building CLooG or PPL or ISL requires a recent compiler
                    # our best bet is to do a 3-staged build of GCC, and
                    # build CLooG/PPL/ISL with the GCC we're building in stage 2
                    # then (bootstrap) build GCC in stage 3
                    # also, no need to stage cloog/ppl/isl in stage3 (may even cause troubles)
                    self.stagedbuild = True
                    extra_src_dirs.remove(extra)

            # try and find source directories with given prefixes
            # these sources should be included in list of sources in .eb spec file,
            # so EasyBuild can unpack them in the build dir
            found_src_dirs = []
            versions = {}
            names = {}
            all_dirs = os.listdir(self.builddir)
            for d in all_dirs:
                for sd in extra_src_dirs:
                    if d.startswith(sd):
                        found_src_dirs.append({
                            'source_dir': d,
                            'target_dir': sd
                        })
                        # expected format: get_name[-subname]-get_version
                        ds = os.path.basename(d).split('-')
                        name = '-'.join(ds[0:-1])
                        names.update({sd: name})
                        ver = ds[-1]
                        versions.update({sd: ver})

            # we need to find all dirs specified, or else...
            if not len(found_src_dirs) == len(extra_src_dirs):
                raise EasyBuildError("Couldn't find all source dirs %s: found %s from %s",
                                     extra_src_dirs, found_src_dirs, all_dirs)

            # copy to a dir with name as expected by GCC build framework
            for d in found_src_dirs:
                src = os.path.join(self.builddir, d['source_dir'])
                if target_prefix:
                    dst = os.path.join(target_prefix, d['target_dir'])
                else:
                    dst = os.path.join(self.cfg['start_dir'], d['target_dir'])
                if not os.path.exists(dst):
                    try:
                        shutil.copytree(src, dst)
                    except OSError, err:
                        raise EasyBuildError("Failed to copy src %s to dst %s: %s", src, dst, err)
                    self.log.debug("Copied %s to %s, so GCC can build %s" % (src, dst, d['target_dir']))
                else:
                    self.log.debug("No need to copy %s to %s, it's already there." % (src, dst))
        else:
            # in versions prior to GCC v4.5, there's no support for extra source dirs, so return only empty info
            configopts = ''
            names = {}
            versions = {}

        return {
            'configopts': configopts,
            'names': names,
            'versions': versions
        }

    def run_configure_cmd(self, cmd):
        """
        Run a configure command, with some extra checking (e.g. for unrecognized options).
        """
        (out, ec) = run_cmd("%s %s" % (self.cfg['preconfigopts'], cmd), log_all=True, simple=False)

        if ec != 0:
            raise EasyBuildError("Command '%s' exited with exit code != 0 (%s)", cmd, ec)

        # configure scripts tend to simply ignore unrecognized options
        # we should be more strict here, because GCC is very much a moving target
        unknown_re = re.compile("WARNING: unrecognized options")

        unknown_options = unknown_re.findall(out)
        if unknown_options:
            raise EasyBuildError("Unrecognized options found during configure: %s", unknown_options)

    def configure_step(self):
        """
        Configure for GCC build:
        - prepare extra source dirs (GMP, MPFR, MPC, ...)
        - create obj dir to build in (GCC doesn't like to be built in source dir)
        - add configure and make options, according to .eb spec file
        - decide whether or not to do a staged build (which is required to enable PPL/CLooG support)
        - set platform_lib based on config.guess output
        """

        # self.configopts will be reused in a 3-staged build,
        # configopts is only used in first configure
        self.configopts = self.cfg['configopts']

        # I) prepare extra source dirs, e.g. for GMP, MPFR, MPC (if required), so GCC can build them
        stage1_info = self.prep_extra_src_dirs("stage1")
        configopts = stage1_info['configopts']

        # II) update config options

        # enable specified language support
        if self.cfg['languages']:
            self.configopts += " --enable-languages=%s" % ','.join(self.cfg['languages'])

        # enable link-time-optimization (LTO) support, if desired
        if self.cfg['withlto']:
            self.configopts += " --enable-lto"

        # configure for a release build
        self.configopts += " --enable-checking=release "
        # enable multilib: allow both 32 and 64 bit
        if self.cfg['multilib']:
            glibc_32bit = [
                "glibc.i686",  # Fedora, RedHat-based
                "glibc.ppc",   # "" on Power
                "libc6-dev-i386",  # Debian-based
                "gcc-c++-32bit",  # OpenSuSE, SLES
            ]
            if not any([check_os_dependency(dep) for dep in glibc_32bit]):
                raise EasyBuildError("Using multilib requires 32-bit glibc (install one of %s, depending on your OS)",
                                     ', '.join(glibc_32bit))
            self.configopts += " --enable-multilib --with-multilib-list=m32,m64"
        else:
            self.configopts += " --disable-multilib"
        # build both static and dynamic libraries (???)
        self.configopts += " --enable-shared=yes --enable-static=yes "
        # use POSIX threads
        self.configopts += " --enable-threads=posix "
        # use GOLD as default linker, enable plugin support
        self.configopts += " --enable-gold=default --enable-plugins "
        self.configopts += " --enable-ld --with-plugin-ld=ld.gold"

        # enable bootstrap build for self-containment (unless for staged build)
        if not self.stagedbuild:
            configopts += " --enable-bootstrap"
        else:
            configopts += " --disable-bootstrap"

        if self.stagedbuild:
            #
            # STAGE 1: configure GCC build that will be used to build PPL/CLooG
            #
            self.log.info("Starting with stage 1 of 3-staged build to enable CLooG and/or PPL, ISL support...")
            self.stage1installdir = os.path.join(self.builddir, 'GCC_stage1_eb')
            configopts += " --prefix=%(p)s --with-local-prefix=%(p)s" % {'p': self.stage1installdir}

        else:
            # unstaged build, so just run standard configure/make/make install
            # set prefixes
            self.log.info("Performing regular GCC build...")
            configopts += " --prefix=%(p)s --with-local-prefix=%(p)s" % {'p': self.installdir}

        # III) create obj dir to build in, and change to it
        #     GCC doesn't like to be built in the source dir
        if self.stagedbuild:
            self.stage1prefix = self.create_dir("stage1_obj")
        else:
            self.create_dir("obj")

        # IV) actual configure, but not on default path
        cmd = "../configure  %s %s" % (self.configopts, configopts)

        # instead of relying on uname, we run the same command GCC uses to
        # determine the platform
        out, ec = run_cmd("../config.guess", simple=False)
        if ec == 0:
            self.platform_lib = out.rstrip()

        self.run_configure_cmd(cmd)

    def build_step(self):

        if self.stagedbuild:

            # make and install stage 1 build of GCC
            paracmd = ''
            if self.cfg['parallel']:
                paracmd = "-j %s" % self.cfg['parallel']

            cmd = "%s make %s %s" % (self.cfg['prebuildopts'], paracmd, self.cfg['buildopts'])
            run_cmd(cmd, log_all=True, simple=True)

            cmd = "make install %s" % (self.cfg['installopts'])
            run_cmd(cmd, log_all=True, simple=True)

            # register built GCC as compiler to use for stage 2/3
            path = "%s/bin:%s" % (self.stage1installdir, os.getenv('PATH'))
            env.setvar('PATH', path)

            ld_lib_path = "%(dir)s/lib64:%(dir)s/lib:%(val)s" % {
                'dir': self.stage1installdir,
                'val': os.getenv('LD_LIBRARY_PATH')
            }
            env.setvar('LD_LIBRARY_PATH', ld_lib_path)

            #
            # STAGE 2: build GMP/PPL/CLooG for stage 3
            #

            # create dir to build GMP/PPL/CLooG in
            stage2dir = "stage2_stuff"
            stage2prefix = self.create_dir(stage2dir)

            # prepare directories to build GMP/PPL/CLooG
            stage2_info = self.prep_extra_src_dirs("stage2", target_prefix=stage2prefix)
            configopts = stage2_info['configopts']

            # build PPL and CLooG (GMP as dependency)

            for lib in ["gmp"] + self.with_dirs:
                self.log.debug("Building %s in stage 2" % lib)
                if lib == "gmp" or self.cfg['with%s' % lib]:
                    libdir = os.path.join(stage2prefix, lib)
                    try:
                        os.chdir(libdir)
                    except OSError, err:
                        raise EasyBuildError("Failed to change to %s: %s", libdir, err)
                    if lib == "gmp":
                        cmd = "./configure --prefix=%s " % stage2prefix
                        cmd += "--with-pic --disable-shared --enable-cxx"
                    elif lib == "ppl":
                        self.pplver = LooseVersion(stage2_info['versions']['ppl'])

                        cmd = "./configure --prefix=%s --with-pic -disable-shared " % stage2prefix
                        # only enable C/C++ interfaces (Java interface is sometimes troublesome)
                        cmd += "--enable-interfaces='c c++' "

                        # enable watchdog (or not)
                        if self.pplver <= LooseVersion("0.11"):
                            if self.cfg['pplwatchdog']:
                                cmd += "--enable-watchdog "
                            else:
                                cmd += "--disable-watchdog "
                        elif self.cfg['pplwatchdog']:
                            raise EasyBuildError("Enabling PPL watchdog only supported in PPL <= v0.11 .")

                        # make sure GMP we just built is found
                        cmd += "--with-gmp=%s " % stage2prefix
                    elif lib == "isl":
                        cmd = "./configure --prefix=%s --with-pic --disable-shared " % stage2prefix
                        cmd += "--with-gmp=system --with-gmp-prefix=%s " % stage2prefix
                    elif lib == "cloog":
                        self.cloogname = stage2_info['names']['cloog']
                        self.cloogver = LooseVersion(stage2_info['versions']['cloog'])
                        v0_15 = LooseVersion("0.15")
                        v0_16 = LooseVersion("0.16")

                        cmd = "./configure --prefix=%s --with-pic --disable-shared " % stage2prefix

                        # use ISL or PPL
                        if self.cfg['clooguseisl']:
                            if self.cfg['withisl']:
                                self.log.debug("Using external ISL for CLooG")
                                cmd += "--with-isl=system --with-isl-prefix=%s " % stage2prefix
                            elif self.cloogver >= v0_16:
                                self.log.debug("Using bundled ISL for CLooG")
                                cmd += "--with-isl=bundled "
                            else:
                                raise EasyBuildError("Using ISL is only supported in CLooG >= v0.16 (detected v%s).",
                                                     self.cloogver)
                        else:
                            if self.cloogname == "cloog-ppl" and self.cloogver >= v0_15 and self.cloogver < v0_16:
                                cmd += "--with-ppl=%s " % stage2prefix
                            else:
                                errormsg = "PPL only supported with CLooG-PPL v0.15.x (detected v%s)" % self.cloogver
                                errormsg += "\nNeither using PPL or ISL-based ClooG, I'm out of options..."
                                raise EasyBuildError(errormsg)

                        # make sure GMP is found
                        if self.cloogver >= v0_15 and self.cloogver < v0_16:
                            cmd += "--with-gmp=%s " % stage2prefix
                        elif self.cloogver >= v0_16:
                            cmd += "--with-gmp=system --with-gmp-prefix=%s " % stage2prefix
                        else:
                            raise EasyBuildError("Don't know how to specify location of GMP to configure of CLooG v%s.",
                                                 self.cloogver)
                    else:
                        raise EasyBuildError("Don't know how to configure for %s", lib)

                    # configure
                    self.run_configure_cmd(cmd)

                    # build and 'install'
                    cmd = "make %s" % paracmd
                    run_cmd(cmd, log_all=True, simple=True)

                    cmd = "make install"
                    run_cmd(cmd, log_all=True, simple=True)

                    if lib == "gmp":
                        # make sure correct GMP is found
                        libpath = os.path.join(stage2prefix, 'lib')
                        incpath = os.path.join(stage2prefix, 'include')

                        cppflags = os.getenv('CPPFLAGS', '')
                        env.setvar('CPPFLAGS', "%s -L%s -I%s " % (cppflags, libpath, incpath))

            #
            # STAGE 3: bootstrap build of final GCC (with PPL/CLooG support)
            #

            # create new obj dir and change into it
            self.create_dir("stage3_obj")

            # reconfigure for stage 3 build
            self.log.info("Stage 2 of 3-staged build completed, continuing with stage 2 "
                          "(with CLooG and/or PPL, ISL support enabled)...")

            stage3_info = self.prep_extra_src_dirs("stage3")
            configopts = stage3_info['configopts']
            configopts += " --prefix=%(p)s --with-local-prefix=%(p)s" % {'p': self.installdir}

            # enable bootstrapping for self-containment
            configopts += " --enable-bootstrap "

            # PPL config options
            if self.cfg['withppl']:
                # for PPL build and CLooG-PPL linking
                for lib in ["lib64", "lib"]:
                    path = os.path.join(self.stage1installdir, lib, "libstdc++.a")
                    if os.path.exists(path):
                        libstdcxxpath = path
                        break
                configopts += "--with-host-libstdcxx='-static-libgcc %s -lm' " % libstdcxxpath

                configopts += "--with-ppl=%s " % stage2prefix

                if self.pplver <= LooseVersion("0.11"):
                    if self.cfg['pplwatchdog']:
                        configopts += "--enable-watchdog "
                    else:
                        configopts += "--disable-watchdog "

            # CLooG config options
            if self.cfg['withcloog']:
                configopts += "--with-cloog=%s " % stage2prefix

                if self.cfg['clooguseisl'] and self.cloogver >= LooseVersion("0.16") and LooseVersion(self.version) < LooseVersion("4.8.0"):
                    configopts += "--enable-cloog-backend=isl "

            if self.cfg['withisl']:
                configopts += "--with-isl=%s " % stage2prefix

            # configure
            cmd = "../configure %s %s" % (self.configopts, configopts)
            self.run_configure_cmd(cmd)

        # build with bootstrapping for self-containment
        self.cfg.update('buildopts', 'bootstrap')

        # call standard build_step
        super(EB_GCC, self).build_step()

    # make install is just standard install_step, nothing special there

    def sanity_check_step(self):
        """
        Custom sanity check for GCC
        """

        os_type = get_os_type()
        sharedlib_ext = get_shared_lib_ext()
        common_infix = os.path.join('gcc', self.platform_lib, self.version)

        bin_files = ["gcov"]
        lib_files = []
        if LooseVersion(self.version) >= LooseVersion('4.2'):
            # libgomp was added in GCC 4.2.0
            ["libgomp.%s" % sharedlib_ext, "libgomp.a"]
        if os_type == 'Linux':
            lib_files.extend(["libgcc_s.%s" % sharedlib_ext])
            # libmudflap is replaced by asan (see release notes gcc 4.9.0)
            if LooseVersion(self.version) < LooseVersion("4.9.0"):
                lib_files.extend(["libmudflap.%s" % sharedlib_ext, "libmudflap.a"])
            else:
                lib_files.extend(["libasan.%s" % sharedlib_ext, "libasan.a"])
        libexec_files = []
        dirs = ['lib/%s' % common_infix]

        if not self.cfg['languages']:
            # default languages are c, c++, fortran
            bin_files = ["c++", "cpp", "g++", "gcc", "gcov", "gfortran"]
            lib_files.extend(["libstdc++.%s" % sharedlib_ext, "libstdc++.a"])
            libexec_files = ['cc1', 'cc1plus', 'collect2', 'f951']

        if 'c' in self.cfg['languages']:
            bin_files.extend(['cpp', 'gcc'])

        if 'c++' in self.cfg['languages']:
            bin_files.extend(['c++', 'g++'])
            dirs.append('include/c++/%s' % self.version)
            lib_files.extend(["libstdc++.%s" % sharedlib_ext, "libstdc++.a"])

        if 'fortran' in self.cfg['languages']:
            bin_files.append('gfortran')
            lib_files.extend(['libgfortran.%s' % sharedlib_ext, 'libgfortran.a'])

        if self.cfg['withlto']:
            libexec_files.extend(['lto1', 'lto-wrapper'])
            if os_type in ['Linux']:
                libexec_files.append('liblto_plugin.%s' % sharedlib_ext)

        bin_files = ["bin/%s" % x for x in bin_files]
        libdirs64 = ['lib64']
        libdirs32 = ['lib', 'lib32']
        libdirs = libdirs64 + libdirs32
        if self.cfg['multilib']:
            # with multilib enabled, both lib and lib64 should be there
            lib_files64 = [os.path.join(libdir, x) for libdir in libdirs64 for x in lib_files]
            lib_files32 = [tuple([os.path.join(libdir, x) for libdir in libdirs32]) for x in lib_files]
            lib_files = lib_files64 + lib_files32
        else:
            # lib64 on SuSE and Darwin, lib otherwise
            lib_files = [tuple([os.path.join(libdir, x) for libdir in libdirs]) for x in lib_files]
        # lib on SuSE, libexec otherwise
        libdirs = ['libexec', 'lib']
        libexec_files = [tuple([os.path.join(libdir, common_infix, x) for libdir in libdirs]) for x in libexec_files]

        custom_paths = {
            'files': bin_files + lib_files + libexec_files,
            'dirs': dirs,
        }

        super(EB_GCC, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """
        Make sure all GCC libs are in LD_LIBRARY_PATH
        """
        guesses = super(EB_GCC, self).make_module_req_guess()
        guesses.update({
            'PATH': ['bin'],
            'LD_LIBRARY_PATH': ['lib', 'lib64',
                                'lib/gcc/%s/%s' % (self.platform_lib, self.cfg['version'])],
            'MANPATH': ['man', 'share/man']
        })
        return guesses
