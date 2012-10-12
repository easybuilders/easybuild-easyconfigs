# This file is an EasyBuild recipy as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright (c) 2012 University of Luxembourg / LCSB
# Author::    Cedric Laczny <cedric.laczny@uni.lu>, Fotis Georgatos <fotis.georgatos@uni.lu>
# License::   MIT/GPL
# File::      $File$ 
# Date::      $Date$
"""
Easybuild support for building SAMtools (SAM - Sequence Alignment/Map)
"""

import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake


class EB_SAMtools(ConfigureMake):
    """
    Support for building SAMtools; SAM (Sequence Alignment/Map) format
    is a generic format for storing large nucleotide sequence alignments.
    """

    def __init__(self, *args, **kwargs):
        """Define lists of files to install."""
        super(EB_SAMtools, self).__init__(*args, **kwargs)

        self.bin_files = ["bcftools/vcfutils.pl", "bcftools/bcftools", "misc/blast2sam.pl",
                          "misc/bowtie2sam.pl", "misc/export2sam.pl", "misc/interpolate_sam.pl",
                          "misc/novo2sam.pl", "misc/psl2sam.pl", "misc/sam2vcf.pl", "misc/samtools.pl",
                          "misc/soap2sam.pl", "misc/varfilter.py", "misc/wgsim_eval.pl",
                          "misc/zoom2sam.pl", "misc/md5sum-lite", "misc/md5fa", "misc/maq2sam-short",
                          "misc/maq2sam-long", "misc/wgsim", "misc/seqtk", "samtools"]
        self.lib_files = ["libbam.a"]
        self.include_files = ["bam.h", "bam2bcf.h", "bam_endian.h", "bgzf.h", "errmod.h", "faidx.h", "kaln.h",
                              "khash.h", "klist.h", "knetfile.h", "kprobaln.h", "kseq.h", "ksort.h", "kstring.h",
                              "razf.h", "sam.h", "sam_header.h", "sample.h"]

    def configure_step(self):
        """
        No configure
        """
        pass

    def install_step(self):
        """
        Install by copying files to install dir
        """

        for (srcdir, dest, files) in [
                                      (self.cfg['start_dir'], 'bin', self.bin_files),
                                      (self.cfg['start_dir'], 'lib', self.lib_files),
                                      (self.cfg['start_dir'], 'include/bam', self.include_files)
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
        """Custom sanity check for SAMtools."""

        custom_paths = {
                        'files': ['bin/%s' % x for x in [f.split('/')[-1] for f in self.bin_files]] +
                                 ['lib/%s' % x for x in self.lib_files] +
                                 ['include/bam/%s' % x for x in self.include_files],
                        'dirs': []
                       }

        super(EB_SAMtools, self).sanity_check_step(custom_paths=custom_paths)
