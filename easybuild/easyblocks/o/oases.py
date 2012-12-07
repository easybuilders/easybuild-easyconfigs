# This file is an EasyBuild recipy as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright (c) 2012 University of Luxembourg / LCSB
# Author::    Cedric Laczny <cedric.laczny@uni.lu>, Fotis Georgatos <fotis.georgatos@uni.lu>
# License::   MIT/GPL
# File::      $File$ 
# Date::      $Date$


import os
import shutil
import fileinput
import re
import sys 
from easybuild.tools.filetools import run_cmd

from easybuild.easyblocks.generic.configuremake import ConfigureMake

class EB_Oases(ConfigureMake):
    """
    Support for building oases (De novo transcriptome assembler for very short reads)
    """

    def configure_step(self):
        """
        Check if system is suitable apparently via "make check"
        """
        pass

    def build_step(self):
        """
        Needs to get the path of the build-dir of velvet -> requires headers
        """
        builddep = self.cfg['builddependencies']
        # assert that it only has ONE builddep specified
        assert len(builddep) == 1

        #srcdir = self.cfg['startfrom']
        srcdir = self.builddir

        print builddep
        velvet = builddep[0][0]
        velvetver = builddep[0][1]

        cmd = 'make VELVET_DIR="' + os.path.join(srcdir, velvet.lower() + "_" + velvetver) + '"'
        run_cmd(cmd, log_all = True, simple = True)

    def install_step(self):
        """
        Install by copying files to install dir
        """
        srcdir = self.cfg['start_dir']
        destdir = os.path.join(self.installdir, 'bin')
        srcfile = None
        # Get executable files, something like: for i in $(find . -maxdepth 1 -type f -perm +111 -print | \
        #    sed -e 's/\.\///g' | awk '{print "\""$0"\""}' | grep -vE "\.sh|\.html"); do echo -ne "$i, "; done && echo
        try:
            os.makedirs(destdir)
            for filename in ["oases"]:
                srcfile = os.path.join(srcdir, filename)
                shutil.copy2(srcfile, destdir)
        except OSError, err:
            self.log.exception("Copying %s to installation dir %s failed: %s" % (srcfile, destdir, err))

