# This file is an EasyBuild recipy as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright (c) 2012 University of Luxembourg / LCSB
# Author::    Cedric Laczny <cedric.laczny@uni.lu>, Fotis Georgatos <fotis.georgatos@uni.lu>
# License::   MIT/GPL
# File::      $File$ 
# Date::      $Date$


import os
import shutil
from easybuild.framework.application import Application

class EB_MUMmer(Application):
    """
    Support for building MUMmer (rapidly aligning entire genomes)
    - build with make install 
    """

    def configure(self):
        """
        Check if system is suitable apparently via "make check"
        """

    def make(self):
      Application.make_install(self)

    def make_install(self):
        """
        Install by copying files to install dir
        """
        srcdir = self.getcfg('startfrom')
        destdir = os.path.join(self.installdir, 'bin')
        srcfile = None
	# Get executable files: for i in $(find . -maxdepth 1 -type f -perm +111 -print | sed -e 's/\.\///g' | awk '{print "\""$0"\""}' | grep -vE "\.sh|\.html"); do echo -ne "$i, "; done && echo
        try:
            os.makedirs(destdir)
            for filename in ["mummer", "annotate", "combineMUMs", "delta-filter", "gaps", "mgaps", "repeat-match", "show-aligns", "show-coords", "show-tiling", "show-snps", "show-diff", "exact-tandems", "mapview", "mummerplot", "nucmer", "promer", "run-mummer1", "run-mummer3", "nucmer2xfig", "dnadiff"]:
                srcfile = os.path.join(srcdir, filename)
                shutil.copy2(srcfile, destdir)
        except OSError, err:
            self.log.exception("Copying %s to installation dir %s failed: %s" % (srcfile, destdir, err))
	
	# Take care of the aux_bin files
	srcdir = os.path.join(srcdir, 'aux_bin')
        destdir = os.path.join(self.installdir, 'bin', 'aux_bin')
        srcfile = None
	# Get executable files: for i in $(find . -maxdepth 1 -type f -perm +111 -print | sed -e 's/\.\///g' | awk '{print "\""$0"\""}' | grep -vE "\.sh|\.html"); do echo -ne "$i, "; done && echo
        try:
            os.makedirs(destdir)
            for filename in ["postnuc", "postpro", "prenuc", "prepro"]:
                srcfile = os.path.join(srcdir, filename)
                shutil.copy2(srcfile, destdir)
        except OSError, err:
            self.log.exception("Copying %s to installation dir %s failed: %s" % (srcfile, destdir, err))

