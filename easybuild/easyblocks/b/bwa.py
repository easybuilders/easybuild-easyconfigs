## 
# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2012-2013 University of Luxembourg/Luxembourg Centre for Systems Biomedicine
# Authors::   Cedric Laczny <cedric.laczny@uni.lu>, Fotis Georgatos <fotis.georgatos@uni.lu>, Kenneth Hoste
# License::   MIT/GPL
# $Id$
#
# This work implements a part of the HPCBIOS project and is a component of the policy:
# http://hpcbios.readthedocs.org/en/latest/HPCBIOS_2012-94.html
##
"""
EasyBuild support for building and installing BWA, implemented as an easyblock

@author: Cedric Laczny (Uni.Lu)
@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
"""

import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake


class EB_BWA(ConfigureMake):
    """
    Support for building BWA
    """

    def configure_step(self):
        """
	    Empty function as bwa comes with _no_ configure script
	    """
        pass

    def install_step(self):
        """
	    Install by copying files to install dir
	    """
        srcdir = self.cfg['start_dir']
        destdir = os.path.join(self.installdir, 'bin')
        srcfile = None
        try:
            os.makedirs(destdir)
            for filename in ["bwa", "qualfa2fq.pl", "solid2fastq.pl", "xa2multi.pl"]:
                srcfile = os.path.join(srcdir, filename)
                shutil.copy2(srcfile, destdir)
        except OSError, err:
            self.log.error("Copying %s to installation dir %s failed: %s" % (srcfile, destdir, err))

    def sanity_check_step(self):
        """Custom sanity check for BWA."""

        custom_paths = {
                        'files': ["bin/%s" % x for x in ["bwa", "qualfa2fq.pl", "solid2fastq.pl", "xa2multi.pl"]],
                        'dirs': []
                       }

        super(EB_BWA, self).sanity_check_step(custom_paths=custom_paths)
