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

class EB_BWA(Application):
    """
    Support for building bwa (ifast and sensitive read alignment)
    - create Make.UNKNOWN
    - build with make and install
    """

    def configure(self):
        """
	Empty function as bwa comes with _no_ configure script
	"""

    def make_install(self):
        """
	Install by copying files to install dir
	"""
        srcdir = self.getcfg('startfrom')
        destdir = os.path.join(self.installdir, 'bin')
        srcfile = None
        try:
            os.makedirs(destdir)
            for filename in ["bwa", "qualfa2fq.pl", "solid2fastq.pl", "xa2multi.pl"]:
                srcfile = os.path.join(srcdir, filename)
                shutil.copy2(srcfile, destdir)
        except OSError, err:
            self.log.exception("Copying %s to installation dir %s failed: %s" % (srcfile, destdir, err))

