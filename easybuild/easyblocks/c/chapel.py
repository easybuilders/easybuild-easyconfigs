# This file is an EasyBuild recipy as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright (c) 2012 University of Luxembourg / Luxembourg Centre for Systems Biomedicine
# Author::    Fotis Georgatos <fotis.georgatos@uni.lu>
# License::   MIT/GPL
# File::      $File$ 
# Date::      $Date$

"""
EasyBuild support for Chapel, implemented as an easyblock
"""
import os
import shutil

import easybuild.tools.toolkit as toolchain
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.filetools import run_cmd


class EB_Chapel(EasyBlock):
    """Support for building Chapel."""


    def __init__(self, *args, **kwargs):
        """Initialize Chapel-specific variables."""
        super(EB_Chapel, self).__init__(*args, **kwargs)
        self.build_in_installdir = True


    def configure_step(self):
        """Configure Chapel build using custom tools"""

        pass


    def build_step(self):
        """Build and install Chapel"""

        # enable parallel build
        p = self.cfg['parallel']
        self.par = ""
        if p:
            self.par = "-j %s" % p

        # build chapel
        cmd = "make %s" % self.par
        run_cmd(cmd, log_all=True, simple=True, log_output=True)


    def install_step(self):
      """Installation of Chapel has alredy been done as part of the build procedure"""

	pass


    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for; this is needed since bin/linux64 of chapel is non standard
        """
        return {
                'PATH':['bin', 'bin/linux64', 'bin64'],
                'LD_LIBRARY_PATH':['lib', 'lib/linux64', 'lib64'],
               }

