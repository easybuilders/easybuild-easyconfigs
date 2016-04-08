##
# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2013-2016 CaSToRC, The Cyprus Institute
# Authors::   George Tsouloupas <g.tsouloupas@cyi.ac.cy>
# License::   MIT/GPL
# $Id$
#
##
"""
Easybuild support for building NAMD, implemented as an easyblock

@author: George Tsouloupas (Cyprus Institute)
@author: Kenneth Hoste (Ghent University)
"""
import glob
import os
import re
import shutil
from distutils.version import LooseVersion

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.makecp import MakeCp
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import extract_file
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd


class EB_NAMD(MakeCp):
    """
    Support for building NAMD
    """
    @staticmethod
    def extra_options():
        """Define extra NAMD-specific easyconfig parameters."""
        extra = MakeCp.extra_options()
        # files_to_copy is not mandatory here
        extra['files_to_copy'][2] = CUSTOM
        extra.update({
            # see http://charm.cs.illinois.edu/manuals/html/charm++/A.html
            'charm_arch': [None, "Charm++ target architecture", MANDATORY],
            'charm_opts': ['--with-production', "Charm++ build options", CUSTOM],
            'namd_basearch': ['Linux-x86_64', "NAMD base target architecture (compiler family is appended", CUSTOM],
            'namd_cfg_opts': ['', "NAMD configure options", CUSTOM],
            'runtest': [True, "Run NAMD test case after building", CUSTOM],
        })
        return extra

    def __init__(self,*args,**kwargs):
        """Custom easyblock constructor for NAMD, initialize class variables."""
        super(EB_NAMD, self).__init__(*args, **kwargs)
        self.namd_arch = None

    def configure_step(self):
        """Custom configure step for NAMD, we build charm++ first (if required)."""

        # complete Charm ++ and NAMD architecture string with compiler family
        comp_fam = self.toolchain.comp_family()
        if self.toolchain.options['usempi']:
            charm_arch_comp = 'mpicxx'
        else:
            charm_arch_comps = {
                toolchain.GCC: 'gcc',
                toolchain.INTELCOMP: 'icc',
            }
            charm_arch_comp = charm_arch_comps.get(comp_fam, None)
        namd_comps = {
            toolchain.GCC: 'g++',
            toolchain.INTELCOMP: 'icc',
        }
        namd_comp = namd_comps.get(comp_fam, None)
        if charm_arch_comp is None or namd_comp is None:
            raise EasyBuildError("Unknown compiler family, can't complete Charm++/NAMD target architecture.")
        self.cfg.update('charm_arch', charm_arch_comp)

        self.log.info("Updated 'charm_arch': %s" % self.cfg['charm_arch'])
        self.namd_arch = '%s-%s' % (self.cfg['namd_basearch'], namd_comp)
        self.log.info("Completed NAMD target architecture: %s" % self.namd_arch)

        charm_tarballs = glob.glob('charm-*.tar')
        if len(charm_tarballs) != 1:
            raise EasyBuildError("Expected to find exactly one tarball for Charm++, found: %s", charm_tarballs)

        extract_file(charm_tarballs[0], os.getcwd())

        tup = (self.cfg['charm_arch'], self.cfg['charm_opts'], self.cfg['parallel'], os.environ['CXXFLAGS'])
        cmd = "./build charm++ %s %s -j%s %s -DMPICH_IGNORE_CXX_SEEK" % tup
        charm_subdir = '.'.join(os.path.basename(charm_tarballs[0]).split('.')[:-1])
        self.log.debug("Building Charm++ using cmd '%s' in '%s'" % (cmd, charm_subdir))
        run_cmd(cmd, path=charm_subdir)

        # compiler (options)
        self.cfg.update('namd_cfg_opts', '--cc "%s" --cc-opts "%s"' % (os.environ['CC'], os.environ['CFLAGS']))
        self.cfg.update('namd_cfg_opts', '--cxx "%s" --cxx-opts "%s"' % (os.environ['CXX'], os.environ['CXXFLAGS']))

        # NAMD dependencies: CUDA, FFTW
        cuda = get_software_root('CUDA')
        if cuda:
            self.cfg.update('namd_cfg_opts', "--with-cuda --cuda-prefix %s" % cuda)

        fftw = get_software_root('FFTW')
        if fftw:
            if LooseVersion(get_software_version('FFTW')) >= LooseVersion('3.0'):
                if LooseVersion(self.version) >= LooseVersion('2.9'):
                    self.cfg.update('namd_cfg_opts', "--with-fftw3")
                else:
                    raise EasyBuildError("Using FFTW v3.x only supported in NAMD v2.9 and up.")
            else:
                self.cfg.update('namd_cfg_opts', "--with-fftw")
            self.cfg.update('namd_cfg_opts', "--fftw-prefix %s" % fftw)

        namd_charm_arch = "--charm-arch %s" % '-'.join(self.cfg['charm_arch'].strip().split(' '))
        cmd = "./config %s %s %s " % (self.namd_arch, namd_charm_arch, self.cfg["namd_cfg_opts"])
        run_cmd(cmd)

    def build_step(self):
        """Build NAMD for configured architecture"""
        super(EB_NAMD, self).build_step(path=self.namd_arch)

    def test_step(self):
        """Run NAMD test case."""
        if self.cfg['runtest']:
            namdcmd = os.path.join(self.cfg['start_dir'], self.namd_arch, 'namd%s' % self.version.split('.')[0])
            if self.cfg['charm_arch'].startswith('mpi'):
                namdcmd = self.toolchain.mpi_cmd_for(namdcmd, 2)
            cmd = "%(namd)s %(testdir)s" % {
                'namd': namdcmd,
                'testdir': os.path.join(self.cfg['start_dir'], self.namd_arch, 'src', 'alanin'),
            }
            out, ec = run_cmd(cmd, simple=False)
            if ec == 0:
                test_ok_regex = re.compile("(^Program finished.$|End of program\s*$)", re.M)
                if test_ok_regex.search(out):
                    self.log.debug("Test '%s' ran fine." % cmd)
                else:
                    raise EasyBuildError("Test '%s' failed ('%s' not found), output: %s",
                                         cmd, test_ok_regex.pattern, out)
        else:
            self.log.debug("Skipping running NAMD test case after building")

    def install_step(self):
        """Install by copying the correct directory to the install dir"""
        srcdir = os.path.join(self.cfg['start_dir'], self.namd_arch)
        try:
            # copy all files, except for .rootdir (required to avoid cyclic copying)
            for item in [x for x in os.listdir(srcdir) if not x in ['.rootdir']]:
                fullsrc = os.path.join(srcdir, item)
                if os.path.isdir(fullsrc):
                    shutil.copytree(fullsrc, os.path.join(self.installdir, item), symlinks=False)
                elif os.path.isfile(fullsrc):
                    shutil.copy2(fullsrc, self.installdir)
        except OSError, err:
            raise EasyBuildError("Failed to copy NAMD build from %s to install directory: %s", srcdir, err)

    def make_module_extra(self):
        """Add the install directory to PATH"""
        txt = super(EB_NAMD, self).make_module_extra()
        txt += self.module_generator.prepend_paths("PATH", [''])
        return txt

    def sanity_check_step(self):
        """Custom sanity check for NAMD."""
        custom_paths = {
            'files': ['charmrun', 'flipbinpdb', 'flipdcd', 'namd%s' % self.version.split('.')[0], 'psfgen'],
            'dirs': ['inc'],
        }
        super(EB_NAMD, self).sanity_check_step(custom_paths=custom_paths)
