##
# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2013-2014 CaSToRC, The Cyprus Institute
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
import shutil

from easybuild.easyblocks.generic.makecp import MakeCp
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
from easybuild.tools.filetools import extract_file, run_cmd

class EB_NAMD(MakeCp):
    """
    Support for building NAMD
    """
    @staticmethod
    def extra_options():
        """Define extra NAMD-specific easyconfig parameters."""
        extra_vars = [
            ('charm_opts', ['--with-production', "Charm++ build options", CUSTOM]),
            ('namd_arch', [None, "NAMD target architecture", MANDATORY]),
            ('namd_cfg_opts', ['', "NAMD configure options w.r.t. Charm++", CUSTOM]),
        ]
        extra = dict(MakeCp.extra_options(extra_vars=extra_vars))
        # files_to_copy is useless here, and definitely not mandatory, so get rid of it
        del extra['files_to_copy']
        return extra.items()

    def configure_step(self):
        """Custom configure step for NAMD, we build charm++ first (if required)."""

        charm_tarballs = glob.glob('charm-*.tar')
        if len(charm_tarballs) != 1:
            self.log.error("Expected to find exactly one tarball for Charm++, found: %s" % charm_tarballs)

        extract_file(charm_tarballs[0], os.getcwd())

        cmd = "./build charm++ -j%s %s" % (self.cfg['parallel'], self.cfg['charm_opts'])
        charm_subdir = '.'.join(os.path.basename(charm_tarballs[0]).split('.')[:-1])
        self.log.debug("Building Charm++ using cmd '%s' in '%s'" % (cmd, charm_subdir))
        run_cmd(cmd, path=charm_subdir)

        cmd = "./config %s %s " % (self.cfg["namd_arch"], self.cfg["namd_cfg_opts"])
        run_cmd(cmd)

    def build_step(self):
        """Build NAMD for configured architecture"""
        super(EB_NAMD, self).build_step(path=self.cfg['namd_arch'])

    def install_step(self):
        """Install by copying the correct directory to the install dir"""
        srcdir = os.path.join(self.cfg['startdir'], self.cfg['namd_arch'])
        try:
            os.rmdir(self.installdir)  # copytree requires that target is non-existent
            shutil.copytree(srcdir, self.installdir)
        except OSError, err:
            self.log.error("Failed to copy NAMD build from %s to install directory: %s" % (srcdir, err))

    def make_module_extra(self):
        """Add the install directory to PATH"""
        txt = super(EB_NAMD, self).make_module_extra()
        txt += self.moduleGenerator.prepend_paths("PATH", [''])
        return txt
