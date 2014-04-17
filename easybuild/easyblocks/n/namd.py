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
import os
import shutil

from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
from easybuild.tools.filetools import run_cmd

class EB_NAMD(EasyBlock):
    """
    Support for building NAMD
    """
    
    @staticmethod
    def extra_options():
        """Define extra NAMD-specific easyconfig parameters."""
        extra_vars = [
            ('charm_ver', [None, "Charm++ version", CUSTOM]),
            ('charm_opts', ['', "Charm++ build options", CUSTOM]),
            ('namd_charm_opts', ['', "NAMD configure options w.r.t. Charm++", CUSTOM]),
            ('namd_arch', [None, "NAMD target architecture", MANDATORY])
        ]
        return EasyBlock.extra_options(extra=extra_vars)

    def configure_step(self):
        """Custom configure step for NAMD, we build charm++ first (if required)."""

        run_cmd("tar xf charm-"+self.cfg["charm_ver"]+".tar")

        cmd = "./build charm++ " + self.cfg["charm_opts"] 
        cmd += " -j"+str(self.cfg['parallel'])
        cmd += " --with-production"
        run_cmd(cmd, path="charm-" + self.cfg["charm_ver"])

        cmd = "./config " + self.cfg["namd_arch"]  
        cmd += " --charm-arch " + self.cfg["namd_charm_opts"]
        run_cmd(cmd, path=self.src[0]['finalpath'])

    def build_step(self):
        """Build NAMD for configured architecture"""
        cmd = "make -j" + str(self.cfg['parallel'])
        run_cmd(cmd, path=os.path.join(self.src[0]['finalpath'], self.cfg["namd_arch"]))

    def install_step(self):
        """Install by copying the correct directory to the install dir"""
        run_cmd("mkdir -p "+self.installdir)
        run_cmd("cp -aL " + os.path.join(self.src[0]['finalpath'], self.cfg["namd_arch"], "/* ") + " " + self.installdir)   

    def make_module_extra(self):
        """Add the install directory to PATH"""
        txt = super(EB_NAMD, self).make_module_extra()
        txt += self.moduleGenerator.prepend_paths("PATH", [''])
        return txt
