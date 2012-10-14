# This file is an EasyBuild recipy as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright (c) 2012 University of Luxembourg / LCSB
# Author::    Cedric Laczny <cedric.laczny@uni.lu>, Fotis Georgatos <fotis.georgatos@uni.lu>
# License::   MIT/GPL
# File::      $File$ 
# Date::      $Date$
"""
EasyBuild support for building and installing Velvet, implemented as an easyblock
"""

import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake


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
            self.log.error("Copying %s to installation dir %s failed: %s" % (srcfile, destdir, err))

    def sanity_check_step(self):
        """Custom sanity check for Velvet."""

        custom_paths = {
                        'files': ['bin/velvetg', 'bin/velveth'],
                        'dirs': []
                       }

        super(EB_Velvet, self).sanity_check_step(custom_paths=custom_paths)
