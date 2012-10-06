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
from easybuild.framework.application import Application

class EB_SAMtools(Application):
    """
    Support for building SAMtools; SAM (Sequence Alignment/Map) format
    is a generic format for storing large nucleotide sequence alignments.
    """

    def configure(self):
        """
        EMPTY
        """
        pass

    def make_install(self):
        """
        Install by copying files to install dir
        """
        srcdir = self.getcfg('startfrom')
        destdir = os.path.join(self.installdir, 'bin')
        srcfile = None
        try:
            os.makedirs(destdir)
            for filename in ["bcftools/vcfutils.pl", "bcftools/bcftools", "misc/blast2sam.pl", "misc/bowtie2sam.pl",
                             "misc/export2sam.pl", "misc/interpolate_sam.pl", "misc/novo2sam.pl", "misc/psl2sam.pl",
                             "misc/sam2vcf.pl", "misc/samtools.pl", "misc/soap2sam.pl", "misc/varfilter.py",
                             "misc/wgsim_eval.pl", "misc/zoom2sam.pl", "misc/md5sum-lite", "misc/md5fa",
                             "misc/maq2sam-short", "misc/maq2sam-long", "misc/wgsim", "misc/seqtk", "samtools"]:
                srcfile = os.path.join(srcdir, filename)
                shutil.copy2(srcfile, destdir)
        except OSError, err:
            self.log.exception("Copying %s to installation dir %s failed: %s" % (srcfile, destdir, err))

        srcdir = self.getcfg('startfrom')
        destdir = os.path.join(self.installdir, 'lib')
        srcfile = None
        try:
            os.makedirs(destdir)
            for filename in ["libbam.a"]:
                srcfile = os.path.join(srcdir, filename)
                shutil.copy2(srcfile, destdir)
        except OSError, err:
            self.log.exception("Copying %s to installation dir %s failed: %s" % (srcfile, destdir, err))

        srcdir = self.getcfg('startfrom')
        destdir = os.path.join(self.installdir, 'include/bam')
        srcfile = None
        try:
            os.makedirs(destdir)
            for filename in ["bam.h", "bam2bcf.h", "bam_endian.h", "bgzf.h", "errmod.h", "faidx.h", "kaln.h",
                             "khash.h", "klist.h", "knetfile.h", "kprobaln.h", "kseq.h", "ksort.h", "kstring.h",
                             "razf.h", "sam.h", "sam_header.h", "sample.h"]:
                srcfile = os.path.join(srcdir, filename)
                shutil.copy2(srcfile, destdir)
        except OSError, err:
            self.log.exception("Copying %s to installation dir %s failed: %s" % (srcfile, destdir, err))

    def make_module_req_guess(self):
        """  
        A dictionary of possible directories to look for.
        Include CPLUS_INCLUDE_PATH as an addition to default ones
        """
        return {
            'PATH': ['bin'],
            'CPLUS_INCLUDE_PATH': ['include'],
            'LD_LIBRARY_PATH': ['lib', 'lib64'],
            'MANPATH': ['man', 'share/man'],
            'PKG_CONFIG_PATH' : ['lib/pkgconfig'],
        }
