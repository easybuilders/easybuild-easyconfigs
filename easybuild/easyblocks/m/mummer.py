# This file is an EasyBuild recipy as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright (c) 2012 University of Luxembourg / LCSB
# Author::    Cedric Laczny <cedric.laczny@uni.lu>, Fotis Georgatos <fotis.georgatos@uni.lu>
# License::   MIT/GPL
# File::      $File$ 
# Date::      $Date$
"""
EasyBuild support for building and installing MUMmer, implemented as an easyblock
"""

import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake


class EB_MUMmer(ConfigureMake):
    """
    Support for building MUMmer (rapidly aligning entire genomes)
    - build with make install 
    """


    def __init__(self, *args, **kwargs):
        """Define list of bin/aux_bin files."""

        super(EB_MUMmer, self).__init__(*args, **kwargs)

        self.bin_files = ["mummer", "annotate", "combineMUMs", "delta-filter", "gaps", "mgaps",
                          "repeat-match", "show-aligns", "show-coords", "show-tiling", "show-snps",
                          "show-diff", "exact-tandems", "mapview", "mummerplot", "nucmer", "promer",
                          "run-mummer1", "run-mummer3", "nucmer2xfig", "dnadiff"]
        self.aux_bin_files = ["postnuc", "postpro", "prenuc", "prepro"]

    def configure_step(self):
        """No configure"""
        pass

    def build_step(self):
        """Build via 'make install."""
        self.cfg.update('makeopts', 'install')

        super(EB_MUMmer, self).build_step()

    def install_step(self):
        """
        Install by copying files to install dir
        """
        # Get executable files: for i in $(find . -maxdepth 1 -type f -perm +111 -print | sed -e 's/\.\///g' | awk '{print "\""$0"\""}' | grep -vE "\.sh|\.html"); do echo -ne "$i, "; done && echo
        for srcdir, dest, files in [
                                    (self.cfg['start_dir'], 'bin', self.bin_files),
                                    (os.path.join(self.cfg['start_dir'], 'aux_bin'), os.path.join('bin', 'aux_bin'),
                                     self.aux_bin_files)
                                   ]:

            destdir = os.path.join(self.installdir, dest)        
            srcfile = None
            try:
                os.makedirs(destdir)
                for filename in files:
                    srcfile = os.path.join(srcdir, filename)
                    shutil.copy2(srcfile, destdir)
            except OSError, err:
                self.log.error("Copying %s to installation dir %s failed: %s" % (srcfile, destdir, err))

    def sanity_check_step(self):
        """Custom sanity check for MUMmer."""

        custom_paths = {
                        'files': ['bin/%s' % x for x in self.bin_files] +
                                 ['bin/aux_bin/%s' % x for x in self.aux_bin_files],
                        'dirs': []
                       }
        super(EB_MUMmer, self).sanity_check_step(custom_paths=custom_paths)
