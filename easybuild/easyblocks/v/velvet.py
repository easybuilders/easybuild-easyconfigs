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
EasyBuild support for building and installing Velvet, implemented as an easyblock

@author: Cedric Laczny (Uni.Lu)
@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
"""
import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError


class EB_Velvet(ConfigureMake):
    """
    Support for building Velvet
    """

    def configure_step(self):
        """No configuration."""
        pass

    def install_step(self):
        """
        Install by copying files to install dir
        """
        srcdir = self.cfg['start_dir']
        destdir = os.path.join(self.installdir, 'bin')
        srcfile = None
        # Get executable files: for i in $(find . -maxdepth 1 -type f -perm +111 -print | sed -e 's/\.\///g' | awk '{print "\""$0"\""}' | grep -vE "\.sh|\.html"); do echo -ne "$i, "; done && echo
        try:
            os.makedirs(destdir)
            for filename in ["velveth", "velvetg"]:
                srcfile = os.path.join(srcdir, filename)
                shutil.copy2(srcfile, destdir)
        except OSError, err:
            raise EasyBuildError("Copying %s to installation dir %s failed: %s", srcfile, destdir, err)

    def sanity_check_step(self):
        """Custom sanity check for Velvet."""

        custom_paths = {
                        'files': ['bin/velvetg', 'bin/velveth'],
                        'dirs': []
                       }

        super(EB_Velvet, self).sanity_check_step(custom_paths=custom_paths)
