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
EasyBuild support for building and installing OpenFOAM, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Xavier Besseron (University of Luxembourg)
@author: Ward Poelmans (Ghent University)
@author: Balazs Hajgato (Free University Brussels (VUB))
"""

import glob
import os
import re
import shutil
import stat
from distutils.version import LooseVersion

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import adjust_permissions, apply_regex_substitutions, mkdir
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd, run_cmd_qa
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_OpenFOAM(EasyBlock):
    """Support for building and installing OpenFOAM."""

    def __init__(self, *args, **kwargs):
        """Specify that OpenFOAM should be built in install dir."""

        super(EB_OpenFOAM, self).__init__(*args, **kwargs)

        self.build_in_installdir = True

        self.wm_compiler = None
        self.wm_mplib = None
        self.openfoamdir = None
        self.thrdpartydir = None

        if 'extend' in self.name.lower():
            if LooseVersion(self.version) >= LooseVersion('3.0'):
                self.openfoamdir = 'foam-extend-%s' % self.version
            else:
                self.openfoamdir = 'OpenFOAM-%s-ext' % self.version
        else:
            self.openfoamdir = '-'.join([self.name, '-'.join(self.version.split('-')[:2])])
        self.log.debug("openfoamdir: %s" % self.openfoamdir)

    def extract_step(self):
        """Extract sources as expected by the OpenFOAM(-Extend) build scripts."""
        super(EB_OpenFOAM, self).extract_step()
        # make sure that the expected subdir is really there after extracting
        # if not, the build scripts (e.g., the etc/bashrc being sourced) will likely fail
        openfoam_installdir = os.path.join(self.installdir, self.openfoamdir)
        if not os.path.exists(openfoam_installdir):
            self.log.warning("Creating expected directory %s, and moving everything there" % openfoam_installdir)
            try:
                contents_installdir = os.listdir(self.installdir)
                # it's one directory but has a wrong name
                if len(contents_installdir) == 1 and os.path.isdir(os.path.join(self.installdir, contents_installdir[0])):
                    source = os.path.join(self.installdir, contents_installdir[0])
                    target = os.path.join(self.installdir, self.openfoamdir)
                    self.log.debug("Renaming %s to %s", source, target)
                    os.rename(source, target)
                else:
                    mkdir(openfoam_installdir)
                    for fil in contents_installdir:
                        if fil != self.openfoamdir:
                            source = os.path.join(self.installdir, fil)
                            target = os.path.join(openfoam_installdir, fil)
                            self.log.debug("Moving %s to %s", source, target)
                            shutil.move(source, target)
                    os.chdir(openfoam_installdir)
            except OSError, err:
                raise EasyBuildError("Failed to move all files to %s: %s", openfoam_installdir, err)

    def patch_step(self):
        """Adjust start directory and start path for patching to correct directory."""
        self.cfg['start_dir'] = os.path.join(self.installdir, self.openfoamdir)
        super(EB_OpenFOAM, self).patch_step(beginpath=self.cfg['start_dir'])

    def configure_step(self):
        """Configure OpenFOAM build by setting appropriate environment variables."""
        # compiler & compiler flags
        comp_fam = self.toolchain.comp_family()

        extra_flags = ''
        if comp_fam == toolchain.GCC:  # @UndefinedVariable
            self.wm_compiler = 'Gcc'
            if get_software_version('GCC') >= LooseVersion('4.8'):
                # make sure non-gold version of ld is used, since OpenFOAM requires it
                # see http://www.openfoam.org/mantisbt/view.php?id=685
                extra_flags = '-fuse-ld=bfd'

            # older versions of OpenFOAM-Extend require -fpermissive
            if 'extend' in self.name.lower() and LooseVersion(self.version) < LooseVersion('2.0'):
                extra_flags += ' -fpermissive'

        elif comp_fam == toolchain.INTELCOMP:  # @UndefinedVariable
            self.wm_compiler = 'Icc'

            # make sure -no-prec-div is used with Intel compilers
            extra_flags = '-no-prec-div'

        else:
            raise EasyBuildError("Unknown compiler family, don't know how to set WM_COMPILER")

        for env_var in ['CFLAGS', 'CXXFLAGS']:
            env.setvar(env_var, "%s %s" % (os.environ.get(env_var, ''), extra_flags))

        # patch out hardcoding of WM_* environment variables
        # for example, replace 'export WM_COMPILER=Gcc' with ': ${WM_COMPILER:=Gcc}; export WM_COMPILER'
        for script in [os.path.join(self.builddir, self.openfoamdir, x) for x in ['etc/bashrc', 'etc/cshrc']]:
            self.log.debug("Patching out hardcoded $WM_* env vars in %s", script)
            # disable any third party stuff, we use EB controlled builds
            regex_subs = [(r"^(setenv|export) WM_THIRD_PARTY_USE_.*[ =].*$", r"# \g<0>")]
            WM_env_var = ['WM_COMPILER', 'WM_MPLIB', 'WM_THIRD_PARTY_DIR']
            # OpenFOAM >= 3.0.0 can use 64 bit integers
            if 'extend' not in self.name.lower() and LooseVersion(self.version) >= LooseVersion('3.0'):
                WM_env_var.append('WM_LABEL_SIZE')
            for env_var in WM_env_var:
                regex_subs.append((r"^(setenv|export) (?P<var>%s)[ =](?P<val>.*)$" % env_var,
                                   r": ${\g<var>:=\g<val>}; export \g<var>"))

            apply_regex_substitutions(script, regex_subs)

        # inject compiler variables into wmake/rules files
        ldirs = glob.glob(os.path.join(self.builddir, self.openfoamdir, 'wmake', 'rules', 'linux*'))
        langs = ['c', 'c++']
        suffixes = ['', 'Opt']
        wmake_rules_files = [os.path.join(ldir, lang + suff) for ldir in ldirs for lang in langs for suff in suffixes]

        mpicc = os.environ['MPICC']
        mpicxx = os.environ['MPICXX']
        cc_seq = os.environ.get('CC_SEQ', os.environ['CC'])
        cxx_seq = os.environ.get('CXX_SEQ', os.environ['CXX'])

        if self.toolchain.mpi_family() == toolchain.OPENMPI:
            # no -cc/-cxx flags supported in OpenMPI compiler wrappers
            c_comp_cmd = 'OMPI_CC="%s" %s' % (cc_seq, mpicc)
            cxx_comp_cmd = 'OMPI_CXX="%s" %s' % (cxx_seq, mpicxx)
        else:
            # -cc/-cxx should work for all MPICH-based MPIs (including Intel MPI)
            c_comp_cmd = '%s -cc="%s"' % (mpicc, cc_seq)
            cxx_comp_cmd = '%s -cxx="%s"' % (mpicxx, cxx_seq)

        comp_vars = {
            # specify MPI compiler wrappers and compiler commands + sequential compiler that should be used by them
            'cc': c_comp_cmd,
            'CC': cxx_comp_cmd,
            'cOPT': os.environ['CFLAGS'],
            'c++OPT': os.environ['CXXFLAGS'],
        }
        for wmake_rules_file in wmake_rules_files:
            fullpath = os.path.join(self.builddir, self.openfoamdir, wmake_rules_file)
            self.log.debug("Patching compiler variables in %s", fullpath)
            regex_subs = []
            for comp_var, newval in comp_vars.items():
                regex_subs.append((r"^(%s\s*=\s*).*$" % re.escape(comp_var), r"\1%s" % newval))
            apply_regex_substitutions(fullpath, regex_subs)

        # enable verbose build for debug purposes
        # starting with openfoam-extend 3.2, PS1 also needs to be set
        env.setvar("FOAM_VERBOSE", '1')

        # installation directory
        env.setvar("FOAM_INST_DIR", self.installdir)

        # third party directory
        self.thrdpartydir = "ThirdParty-%s" % self.version
        # only if third party stuff is actually installed
        if os.path.exists(self.thrdpartydir):
            os.symlink(os.path.join("..", self.thrdpartydir), self.thrdpartydir)
            env.setvar("WM_THIRD_PARTY_DIR", os.path.join(self.installdir, self.thrdpartydir))

        env.setvar("WM_COMPILER", self.wm_compiler)

        # set to an MPI unknown by OpenFOAM, since we're handling the MPI settings ourselves (via mpicc, etc.)
        # Note: this name must contain 'MPI' so the MPI version of the Pstream library is built (cf src/Pstream/Allwmake)
        self.wm_mplib = "EASYBUILDMPI"
        env.setvar("WM_MPLIB", self.wm_mplib)

        # parallel build spec
        env.setvar("WM_NCOMPPROCS", str(self.cfg['parallel']))

        # OpenFOAM >= 3.0.0 can use 64 bit integers
        if 'extend' not in self.name.lower() and LooseVersion(self.version) >= LooseVersion('3.0'):
            if self.toolchain.options['i8']:
                env.setvar("WM_LABEL_SIZE", '64')
            else:
                env.setvar("WM_LABEL_SIZE", '32')

        # make sure lib/include dirs for dependencies are found
        openfoam_extend_v3 = 'extend' in self.name.lower() and LooseVersion(self.version) >= LooseVersion('3.0')
        if LooseVersion(self.version) < LooseVersion("2") or openfoam_extend_v3:
            self.log.debug("List of deps: %s" % self.cfg.dependencies())
            for dep in self.cfg.dependencies():
                dep_name = dep['name'].upper(),
                dep_root = get_software_root(dep['name'])
                env.setvar("%s_SYSTEM" % dep_name, "1")
                dep_vars = {
                    "%s_DIR": "%s",
                    "%s_BIN_DIR": "%s/bin",
                    "%s_LIB_DIR": "%s/lib",
                    "%s_INCLUDE_DIR": "%s/include",
                }
                for var, val in dep_vars.iteritems():
                    env.setvar(var % dep_name, val % dep_root)
        else:
            for depend in ['SCOTCH', 'METIS', 'CGAL', 'Paraview']:
                dependloc = get_software_root(depend)
                if dependloc:
                    if depend == 'CGAL' and get_software_root('Boost'):
                        env.setvar("CGAL_ROOT", dependloc)
                        env.setvar("BOOST_ROOT", get_software_root('Boost'))
                    else:
                        env.setvar("%s_ROOT" % depend.upper(), dependloc)

    def build_step(self):
        """Build OpenFOAM using make after sourcing script to set environment."""

        precmd = "source %s" % os.path.join(self.builddir, self.openfoamdir, "etc", "bashrc")

        # make directly in install directory
        cmd_tmpl = "%(precmd)s && %(prebuildopts)s %(makecmd)s" % {
            'precmd': precmd,
            'prebuildopts': self.cfg['prebuildopts'],
            'makecmd': os.path.join(self.builddir, self.openfoamdir, '%s'),
        }
        if 'extend' in self.name.lower() and LooseVersion(self.version) >= LooseVersion('3.0'):
            qa = {
                "Proceed without compiling ParaView [Y/n]": 'Y',
                "Proceed without compiling cudaSolvers? [Y/n]": 'Y',
            }
            noqa = [
                ".* -o .*",
                "checking .*",
                "warning.*",
                "configure: creating.*",
                "%s .*" % os.environ['CC'],
                "wmake .*",
                "Making dependency list for source file.*",
                "\s*\^\s*",  # warning indicator
                "Cleaning .*",
            ]
            run_cmd_qa(cmd_tmpl % 'Allwmake.firstInstall', qa, no_qa=noqa, log_all=True, simple=True)
        else:
            run_cmd(cmd_tmpl % 'Allwmake', log_all=True, simple=True, log_output=True)

    def install_step(self):
        """Building was performed in install dir, so just fix permissions."""

        # fix permissions of OpenFOAM dir
        fullpath = os.path.join(self.installdir, self.openfoamdir)
        adjust_permissions(fullpath, stat.S_IROTH, add=True, recursive=True, ignore_errors=True)
        adjust_permissions(fullpath, stat.S_IXOTH, add=True, recursive=True, onlydirs=True, ignore_errors=True)

        # fix permissions of ThirdParty dir and subdirs (also for 2.x)
        # if the thirdparty tarball is installed
        fullpath = os.path.join(self.installdir, self.thrdpartydir)
        if os.path.exists(fullpath):
            adjust_permissions(fullpath, stat.S_IROTH, add=True, recursive=True, ignore_errors=True)
            adjust_permissions(fullpath, stat.S_IXOTH, add=True, recursive=True, onlydirs=True, ignore_errors=True)

    def sanity_check_step(self):
        """Custom sanity check for OpenFOAM"""
        shlib_ext = get_shared_lib_ext()

        # OpenFOAM >= 3.0.0 can use 64 bit integers
        if 'extend' not in self.name.lower() and LooseVersion(self.version) >= LooseVersion('3.0'):
            if self.toolchain.options['i8']:
                int_size = 'Int64'
            else:
                int_size = 'Int32'
        else:
            int_size = ''

        psubdir = "linux64%sDP%sOpt" % (self.wm_compiler, int_size)

        openfoam_extend_v3 = 'extend' in self.name.lower() and LooseVersion(self.version) >= LooseVersion('3.0')
        if openfoam_extend_v3 or LooseVersion(self.version) < LooseVersion("2"):
            toolsdir = os.path.join(self.openfoamdir, "applications", "bin", psubdir)
            libsdir = os.path.join(self.openfoamdir, "lib", psubdir)
            dirs = [toolsdir, libsdir]
        else:
            toolsdir = os.path.join(self.openfoamdir, "platforms", psubdir, "bin")
            libsdir = os.path.join(self.openfoamdir, "platforms", psubdir, "lib")
            dirs = [toolsdir, libsdir]

        # some randomly selected binaries
        # if one of these is missing, it's very likely something went wrong
        bins = [os.path.join(self.openfoamdir, "bin", x) for x in ["foamExec", "paraFoam"]] + \
               [os.path.join(toolsdir, "buoyant%sSimpleFoam" % x) for x in ["", "Boussinesq"]] + \
               [os.path.join(toolsdir, "%sFoam" % x) for x in ["boundary", "engine", "sonic"]] + \
               [os.path.join(toolsdir, "surface%s" % x) for x in ["Add", "Find", "Smooth"]] + \
               [os.path.join(toolsdir, x) for x in ["deformedGeom", "engineSwirl", "modifyMesh",
                                                    "refineMesh", "vorticity"]]
        # check for the Pstream and scotchDecomp libraries, there must be a dummy one and an mpi one
        if 'extend' in self.name.lower():
            libs = [os.path.join(libsdir, "libscotchDecomp.%s" % shlib_ext)]
            if LooseVersion(self.version) < LooseVersion('3.2'):
                libs.extend([os.path.join(libsdir, x, "libPstream.%s" % shlib_ext) for x in ["dummy", "mpi"]])
        else:
            libs = [os.path.join(libsdir, x, "libPstream.%s" % shlib_ext) for x in ["dummy", "mpi"]] + \
                   [os.path.join(libsdir, x, "libptscotchDecomp.%s" % shlib_ext) for x in ["dummy", "mpi"]] +\
                   [os.path.join(libsdir, "libscotchDecomp.%s" % shlib_ext)] + \
                   [os.path.join(libsdir, "dummy", "libscotchDecomp.%s" % shlib_ext)]

        if 'extend' not in self.name.lower() and LooseVersion(self.version) >= LooseVersion("2.3.0"):
            # surfaceSmooth is replaced by surfaceLambdaMuSmooth is OpenFOAM v2.3.0
            bins.remove(os.path.join(toolsdir, "surfaceSmooth"))
            bins.append(os.path.join(toolsdir, "surfaceLambdaMuSmooth"))

        custom_paths = {
            'files': [os.path.join(self.openfoamdir, 'etc', x) for x in ["bashrc", "cshrc"]] + bins + libs,
            'dirs': dirs,
        }

        super(EB_OpenFOAM, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Define extra environment variables required by OpenFOAM"""

        txt = super(EB_OpenFOAM, self).make_module_extra()

        env_vars = [
            ('WM_PROJECT_VERSION', self.version),
            ('FOAM_INST_DIR', self.installdir),
            ('WM_COMPILER', self.wm_compiler),
            ('WM_MPLIB', self.wm_mplib),
            ('FOAM_BASH', os.path.join(self.installdir, self.openfoamdir, 'etc', 'bashrc')),
            ('FOAM_CSH', os.path.join(self.installdir, self.openfoamdir, 'etc', 'cshrc')),
        ]

        # OpenFOAM >= 3.0.0 can use 64 bit integers
        if 'extend' not in self.name.lower() and LooseVersion(self.version) >= LooseVersion('3.0'):
            if self.toolchain.options['i8']:
                env_vars += [('WM_LABEL_SIZE', '64')]
            else:
                env_vars += [('WM_LABEL_SIZE', '32')]

        for (env_var, val) in env_vars:
            # check whether value is defined for compatibility with --module-only
            if val:
                txt += self.module_generator.set_environment(env_var, val)

        return txt
