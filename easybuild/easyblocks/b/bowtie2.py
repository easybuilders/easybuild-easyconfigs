##
# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2012-2016 Uni.Lu/LCSB, NTUA
# Authors::   Cedric Laczny <cedric.laczny@uni.lu>, Fotis Georgatos <fotis@cern.ch>, Kenneth Hoste
# License::   MIT/GPL
# $Id$
#
# This work implements a part of the HPCBIOS project and is a component of the policy:
# http://hpcbios.readthedocs.org/en/latest/HPCBIOS_2012-94.html
##
"""
EasyBuild support for building and installing Bowtie2, implemented as an easyblock

@author: Cedric Laczny (Uni.Lu)
@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
"""

import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError


class EB_Bowtie2(ConfigureMake):
    """
    Support for building bowtie2 (ifast and sensitive read alignment)
    - create Make.UNKNOWN
    - build with make and install 
    """

    def configure_step(self):
        """
        Empty function as bowtie2 comes with _no_ configure script
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
            for filename in ["bowtie2", "bowtie2-align", "bowtie2-build", "bowtie2-inspect"]:
                srcfile = os.path.join(srcdir, filename)
                shutil.copy2(srcfile, destdir)
        except OSError, err:
            raise EasyBuildError("Copying %s to installation dir %s failed: %s", srcfile, destdir, err)

    def sanity_check_step(self):
        """Custom sanity check for Bowtie2."""

        custom_paths = {
                        'files': ['bin/bowtie2', 'bin/bowtie2-align', 'bin/bowtie2-build', 'bin/bowtie2-inspect' ],
                        'dirs': ['.']
                       }

        super(EB_Bowtie2, self).sanity_check_step(custom_paths=custom_paths)

