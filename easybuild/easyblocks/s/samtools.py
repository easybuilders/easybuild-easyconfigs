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
EasyBuild support for building SAMtools (SAM - Sequence Alignment/Map), implemented as an easyblock

@author: Cedric Laczny (Uni.Lu)
@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
"""
import os
import shutil
from distutils.version import LooseVersion

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
                          "misc/maq2sam-long", "misc/wgsim", "samtools"]
        if LooseVersion(self.version) <= LooseVersion('0.1.18'):
            # seqtk is no longer there in v0.1.19
            self.bin_files += ["misc/seqtk"]
        elif LooseVersion(self.version) >= LooseVersion('0.1.19'):
            # new tools in v0.1.19
            self.bin_files += ["misc/ace2sam", "misc/bamcheck","misc/plot-bamcheck","misc/r2plot.lua",
                               "misc/vcfutils.lua"]

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
