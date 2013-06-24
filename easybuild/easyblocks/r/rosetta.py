##
# Copyright 2009-2013 Ghent University
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
EasyBuild support for building and installing Rosetta, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os
import re
import shutil
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.icc import get_icc_version
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.filetools import run_cmd, extract_file
from easybuild.tools.modules import get_software_root, get_software_version


class EB_Rosetta(EasyBlock):
    """Support for building/installing Rosetta."""

    def __init__(self, *args, **kwargs):
        """Add extra config options specific to Rosetta."""
        super(EB_Rosetta, self).__init__(*args, **kwargs)

        self.srcdir = None

    def extract_step(self):
        """Extract sources, if they haven't been already."""
        super(EB_Rosetta, self).extract_step()
        # locate sources, and unpack if necessary
        # old 'bundles' tarballs contain a gzipped tarball for source, recent ones contain unpacked source
        try:
            prefix = os.path.join(self.builddir, '%s-%s' % (self.name, self.version))
            self.srcdir = os.path.join(prefix, 'rosetta_source')
            if not os.path.exists(self.srcdir): 
                src_tarball = os.path.join(prefix, 'rosetta%s_source.tgz' % self.version)
                if os.path.isfile(src_tarball):
                    self.srcdir = extract_file(src_tarball, prefix)
                else:
                    self.log.error("Neither source directory '%s', nor source tarball '%s' found." % (self.srcdir, src_tarball))
        except OSError, err:
            self.log.error("Getting Rosetta sources dir ready failed: %s" % err)

    def configure_step(self):
        """
        Configure build by creating tools/build/user.settings from configure options.
        """
        # construct build options
        defines = ['NDEBUG']
        self.cfg.update('makeopts', "mode=release")

        cxx = os.getenv('CC_SEQ')
        if cxx is None:
            cxx = os.getenv('CC')
        cxx_ver = None
        if self.toolchain.comp_family() in [toolchain.GCC]:  #@UndefinedVariable
            cxx_ver = '.'.join(get_software_version('GCC').split('.')[:2])
        elif self.toolchain.comp_family() in [toolchain.INTELCOMP]:  #@UndefinedVariable
            cxx_ver = '.'.join(get_icc_version().split('.')[:2])
        else:
            self.log.error("Don't know how to determine C++ compiler version.")
        self.cfg.update('makeopts', "cxx=%s cxx_ver=%s" % (cxx, cxx_ver))

        if self.toolchain.options['usempi']:
            self.cfg.update('makeopts', 'extras=mpi')
            defines.extend(['USEMPI', 'MPICH_IGNORE_CXX_SEEK'])

        # create user.settings file
        paths = os.getenv('PATH').split(':')
        ld_library_paths = os.getenv('LD_LIBRARY_PATH').split(':')
        cpaths = os.getenv('CPATH').split(':')
        flags = [str(f).strip('-') for f in self.toolchain.variables['CXXFLAGS'].copy()]

        txt = ''.join([
            'settings = {',
            '   "user" : {',
            '       "prepends" : {',
            '           "library_path"  : %s,' % str(ld_library_paths),
            '           "include_path"  : %s,' % str(cpaths),
            '       },',
            '       "appends" : {',
            '           "program_path"  : %s,' % str(paths),
            '           "flags" : {',
            '               "compile"   : %s,' % str(flags),
            #'               "mode"      : %s,' % str(o_flags),
            '           },',
            '           "defines"       : %s,' % str(defines),
            '       },',
            '       "overrides" : {',
            '           "cc"            : "%s",' % os.getenv('CC'),
            '           "cxx"           : "%s",' % os.getenv('CXX'),
            '           "ENV" : {',
            '               "INTEL_LICENSE_FILE": %s,' % os.getenv('INTEL_LICENSE_FILE'),  # Intel license file
            '               "PATH" : %s,' % str(paths),
            '               "LD_LIBRARY_PATH" : %s,' % str(ld_library_paths),
            '           }',
            '       },',
            '       "removes" : {',
            '       },',
            '   }',
            '}',
        ])
        us_fp = os.path.join(self.srcdir, "tools/build/user.settings")
        try:
            self.log.debug("Creating '%s' with: %s" % (us_fp, txt))
            f = file(us_fp, 'w')
            f.write(txt)
            f.close()
        except IOError, err:
            self.log.error("Failed to write settings file %s: %s" % (us_fp, err))

    def build_step(self):
        """
        Build Rosetta using 'python ./scons.py bin <opts> -j <N>'
        """
        try:
            os.chdir(self.srcdir)
        except OSError, err:
            self.log.error("Failed to change to %s: %s" % (self.srcdir, err))
        par = ''
        if self.cfg['parallel']:
            par = "-j %s" % self.cfg['parallel']
        cmd = "python ./scons.py %s %s bin" % (self.cfg['makeopts'], par)
        run_cmd(cmd, log_all=True, simple=True)

    def install_step(self):
        """
        Copy built files (from e.g. build/src/release/linux/2.6/64/x86/icc/10.0/mpi) to <installpath>/bin,
        and copy (or untar) database and bioTools to install directory
        """
        bindir = os.path.join(self.installdir, 'bin')

        # walk the build/src dir to leaf
        builddir = os.path.join('build', 'src')
        while len(os.listdir(builddir)) == 1:
            builddir = os.path.join(builddir, os.listdir(builddir)[0])

        try:
            self.log.debug("Copying %s to %s" % (builddir, bindir))
            shutil.copytree(builddir, bindir)
        except OSError, err:
            self.log.error("Copying executables from %s to bin dir %s failed: %s" % (builddir, bindir, err))

        os.chdir(self.cfg['start_dir'])

        def extract_and_copy(dirname_tmpl, optional=False):
            """Copy specified directory, after extracting it (if required)."""
            try:
                srcdir = os.path.join(self.cfg['start_dir'], dirname_tmpl % '')
                if not os.path.exists(srcdir): 
                    src_tarball = os.path.join(self.cfg['start_dir'], (dirname_tmpl % self.version) + '.tgz')
                    if os.path.isfile(src_tarball):
                        srcdir = extract_file(src_tarball, self.cfg['start_dir'])
                    elif not optional:
                        self.log.error("Neither source directory '%s', nor source tarball '%s' found." % srcdir, src_tarball)
                shutil.copytree(srcdir, os.path.join(self.installdir, os.path.basename(srcdir)))
            except OSError, err:
                self.log.error("Getting Rosetta sources dir ready failed: %s" % err)

        # (extract and) copy database and biotools (if it's there)
        extract_and_copy('rosetta_database%s')
        extract_and_copy('BioTools%s', optional=True)

    def sanity_check_step(self):

        binaries = ["AbinitioRelax", "backrub", "cluster", "combine_silent", "extract_pdbs",
                    "idealize", "packstat", "relax", "score_jd2", "score"]
        custom_paths = {
            'files':["bin/%s.linux%srelease" % (x, os.getenv('CC')) for x in binaries],
            'dirs':[],
        }
        super(EB_Rosetta, self).sanity_check_step(custom_paths=custom_paths)

