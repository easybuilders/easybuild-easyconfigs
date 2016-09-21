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
EasyBuild support for building and installing Rosetta, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import fileinput
import os
import re
import shutil
import sys
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.icc import get_icc_version
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import extract_file
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_shared_lib_ext


class EB_Rosetta(EasyBlock):
    """Support for building/installing Rosetta."""

    def __init__(self, *args, **kwargs):
        """Add extra config options specific to Rosetta."""
        super(EB_Rosetta, self).__init__(*args, **kwargs)

        self.srcdir = None
        self.cxx = None

    def extract_step(self):
        """Extract sources, if they haven't been already."""
        super(EB_Rosetta, self).extract_step()
        # locate sources, and unpack if necessary
        # old 'bundles' tarballs contain a gzipped tarball for source, recent ones contain unpacked source
        try:
            subdirs = os.listdir(self.builddir)
            if len(subdirs) == 1:
                prefix = os.path.join(self.builddir, subdirs[0])
            else:
                raise EasyBuildError("Found multiple subdirectories, don't know which one to pick: %s", subdirs)
            self.srcdir = os.path.join(prefix, 'rosetta_source')
            if not os.path.exists(self.srcdir):
                self.srcdir = os.path.join(prefix, 'main', 'source')
            if not os.path.exists(self.srcdir): 
                src_tarball = os.path.join(prefix, 'rosetta%s_source.tgz' % self.version)
                if os.path.isfile(src_tarball):
                    self.srcdir = extract_file(src_tarball, prefix)
                else:
                    raise EasyBuildError("Neither source directory '%s', nor source tarball '%s' found.",
                                         self.srcdir, src_tarball)
        except OSError, err:
            raise EasyBuildError("Getting Rosetta sources dir ready failed: %s", err)

    def configure_step(self):
        """
        Configure build by creating tools/build/user.settings from configure options.
        """
        # construct build options
        defines = ['NDEBUG']
        self.cfg.update('buildopts', "mode=release")

        self.cxx = os.getenv('CC_SEQ')
        if self.cxx is None:
            self.cxx = os.getenv('CC')
        cxx_ver = None
        if self.toolchain.comp_family() in [toolchain.GCC]:  #@UndefinedVariable
            cxx_ver = '.'.join(get_software_version('GCC').split('.')[:2])
        elif self.toolchain.comp_family() in [toolchain.INTELCOMP]:  #@UndefinedVariable
            cxx_ver = '.'.join(get_icc_version().split('.')[:2])
        else:
            raise EasyBuildError("Don't know how to determine C++ compiler version.")
        self.cfg.update('buildopts', "cxx=%s cxx_ver=%s" % (self.cxx, cxx_ver))

        if self.toolchain.options.get('usempi', None):
            self.cfg.update('buildopts', 'extras=mpi')
            defines.extend(['USEMPI', 'MPICH_IGNORE_CXX_SEEK'])

        # make sure important environment variables are passed down
        # e.g., compiler env vars for MPI wrappers
        env_vars = {}
        for (key, val) in os.environ.items():
            if key in ['I_MPI_CC', 'I_MPI_CXX', 'MPICH_CC', 'MPICH_CXX', 'OMPI_CC', 'OMPI_CXX']:
                env_vars.update({key: val})
        self.log.debug("List of extra environment variables to pass down: %s" % str(env_vars))

        # create user.settings file
        paths = os.getenv('PATH').split(':')
        ld_library_paths = os.getenv('LD_LIBRARY_PATH').split(':')
        cpaths = os.getenv('CPATH').split(':')
        flags = [str(f).strip('-') for f in self.toolchain.variables['CXXFLAGS'].copy()]

        txt = '\n'.join([
            "settings = {",
            "   'user': {",
            "       'prepends': {",
            "           'library_path': %s," % str(ld_library_paths),
            "           'include_path': %s," % str(cpaths),
            "       },",
            "       'appends': {",
            "           'program_path': %s," % str(paths),
            "           'flags': {",
            "               'compile': %s," % str(flags),
            #"              'mode': %s," % str(o_flags),
            "           },",
            "           'defines': %s," % str(defines),
            "       },",
            "       'overrides': {",
            "           'cc': '%s'," % os.getenv('CC'),
            "           'cxx': '%s'," % os.getenv('CXX'),
            "           'ENV': {",
            "               'INTEL_LICENSE_FILE': '%s'," % os.getenv('INTEL_LICENSE_FILE'),  # Intel license file
            "               'PATH': %s," % str(paths),
            "               'LD_LIBRARY_PATH': %s," % str(ld_library_paths),
        ])
        txt += '\n'
        for (key, val) in env_vars.items():
            txt += "               '%s': '%s',\n" % (key, val)
        txt += '\n'.join([
            "           },",
            "       },",
            "       'removes': {",
            "       },",
            "   },",
            "}",
        ])
        us_fp = os.path.join(self.srcdir, "tools/build/user.settings")
        try:
            self.log.debug("Creating '%s' with: %s" % (us_fp, txt))
            f = file(us_fp, 'w')
            f.write(txt)
            f.close()
        except IOError, err:
            raise EasyBuildError("Failed to write settings file %s: %s", us_fp, err)

        # make sure specified compiler version is accepted by patching it in
        os_fp = os.path.join(self.srcdir, "tools/build/options.settings")
        cxxver_re = re.compile('(.*"%s".*)(,\s*"\*"\s*],.*)' % self.cxx, re.M)
        for line in fileinput.input(os_fp, inplace=1, backup='.orig.eb'):
            line = cxxver_re.sub(r'\1, "%s"\2' % cxx_ver, line)
            sys.stdout.write(line)

    def build_step(self):
        """
        Build Rosetta using 'python ./scons.py bin <opts> -j <N>'
        """
        try:
            os.chdir(self.srcdir)
        except OSError, err:
            raise EasyBuildError("Failed to change to %s: %s", self.srcdir, err)
        par = ''
        if self.cfg['parallel']:
            par = "-j %s" % self.cfg['parallel']
        cmd = "python ./scons.py %s %s bin" % (self.cfg['buildopts'], par)
        run_cmd(cmd, log_all=True, simple=True)

    def install_step(self):
        """
        Copy built files (from e.g. build/src/release/linux/2.6/64/x86/icc/10.0/mpi) to <installpath>/bin,
        and copy (or untar) database and bioTools to install directory
        """
        shlib_ext = get_shared_lib_ext()

        bindir = os.path.join(self.installdir, 'bin')
        libdir = os.path.join(self.installdir, 'lib')
        try:
            os.makedirs(bindir)
            os.makedirs(libdir)
        except OSError, err:
            raise EasyBuildError("Failed to created bin/lib dirs: %s, %s", bindir, libdir)

        for build_subdir in ['src', 'external']:
            builddir = os.path.join('build', build_subdir)
            if not os.path.exists(builddir):
                continue
            # walk the build/src dir to leaf
            try:
                while len(os.listdir(builddir)) == 1:
                    builddir = os.path.join(builddir, os.listdir(builddir)[0])
            except OSError, err:
                raise EasyBuildError("Failed to walk build/src dir: %s", err)
            # copy binaries/libraries to install dir
            lib_re = re.compile("^lib.*\.%s$" % shlib_ext)
            try:
                for fil in os.listdir(builddir):
                    srcfile = os.path.join(builddir, fil)
                    if os.path.isfile(srcfile):
                        if lib_re.match(fil):
                            self.log.debug("Copying %s to %s" % (srcfile, libdir))
                            shutil.copy2(srcfile, os.path.join(libdir, fil))
                        else:
                            self.log.debug("Copying %s to %s" % (srcfile, bindir))
                            shutil.copy2(srcfile, os.path.join(bindir, fil))
            except OSError, err:
                raise EasyBuildError("Copying executables from %s to bin/lib install dirs failed: %s", builddir, err)

        os.chdir(self.cfg['start_dir'])

        def extract_and_copy(dirname_tmpl, optional=False):
            """Copy specified directory, after extracting it (if required)."""
            try:
                srcdir = os.path.join(self.cfg['start_dir'], dirname_tmpl % '')
                if not os.path.exists(srcdir):
                    # try to extract if directory is not there yet
                    src_tarball = os.path.join(self.cfg['start_dir'], (dirname_tmpl % self.version) + '.tgz')
                    if os.path.isfile(src_tarball):
                        srcdir = extract_file(src_tarball, self.cfg['start_dir'])

                if os.path.exists(srcdir):
                    shutil.copytree(srcdir, os.path.join(self.installdir, os.path.basename(srcdir)))
                elif not optional:
                    raise EasyBuildError("Neither source directory '%s', nor source tarball '%s' found.",
                                         srcdir, src_tarball)
            except OSError, err:
                raise EasyBuildError("Getting Rosetta %s dir ready failed: %s", dirname_tmpl, err)

        # (extract and) copy database and biotools (if it's there)
        if os.path.exists(os.path.join(self.cfg['start_dir'], 'main', 'database')):
            extract_and_copy(os.path.join('main', 'database') + '%s')
        else:
            extract_and_copy('rosetta_database%s')

        extract_and_copy('BioTools%s', optional=True)
        if os.path.exists(os.path.join(self.cfg['start_dir'], 'tools')):
            extract_and_copy('tools%s', optional=True)
        else:
            extract_and_copy('rosetta_tools%s', optional=True)

    def sanity_check_step(self):
        """Custom sanity check for Rosetta."""

        infix = ''
        if self.toolchain.options.get('usempi', None):
            infix = 'mpi.'

        binaries = ["AbinitioRelax", "backrub", "cluster", "combine_silent", "extract_pdbs",
                    "idealize_jd2", "packstat", "relax", "score_jd2", "score"]
        custom_paths = {
            'files':["bin/%s.%slinux%srelease" % (x, infix, self.cxx) for x in binaries],
            'dirs':[],
        }
        super(EB_Rosetta, self).sanity_check_step(custom_paths=custom_paths)

