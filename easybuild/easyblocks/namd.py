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
"""

import shutil
from easybuild.framework.easyconfig import CUSTOM
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.filetools import run_cmd
import os

class EB_NAMD(ConfigureMake):
    """
    Support for building NAMD
    """
    def extra_options(extra=None):
        extra_vars = [
                      ('charm_ver', ['', "", CUSTOM]),
                      ('charm_opts', ['', "", CUSTOM]),
                      ('namd_charm_opts', ['', "", CUSTOM]),
                      ('namd_arch', ['', "", CUSTOM])
                     ]
        return extra_vars

    def configure_step(self):
	run_cmd("tar xf charm-"+self.cfg["charm_ver"]+".tar")
	cmd="./build charm++ " + self.cfg["charm_opts"] 
	cmd+=" -j"+str(self.cfg['parallel'])
	cmd+=" --with-production"
	run_cmd(cmd,path="charm-"+self.cfg["charm_ver"])

    def build_step(self):
	cmd=''
	cmd+="./config " + self.cfg["namd_arch"]  
	cmd+=" --charm-arch " + self.cfg["namd_charm_opts"]
	run_cmd(cmd,path=self.src[0]['finalpath'])

	cmd=""
	cmd+="make -j"+str(self.cfg['parallel'])
	run_cmd(cmd,path=self.src[0]['finalpath']+"/"+self.cfg["namd_arch"])

    def install_step(self):
	run_cmd("mkdir -p "+self.installdir)
	run_cmd("cp -aL "+self.src[0]['finalpath']+"/" + self.cfg["namd_arch"] + "/* "+self.installdir)   

    def make_module_extra(self):

        txt = super(EB_NAMD, self).make_module_extra()
        txt += self.moduleGenerator.prepend_paths("PATH", [""])
        self.log.debug("make_module_extra added %s" % txt)
       	return txt

