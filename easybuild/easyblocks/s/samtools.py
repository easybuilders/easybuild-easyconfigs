##
# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2012-2017 Uni.Lu/LCSB, NTUA
# Authors::   Cedric Laczny <cedric.laczny@uni.lu>, Fotis Georgatos <fotis@cern.ch>, Kenneth Hoste
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
from distutils.version import LooseVersion
import os
import shutil
import stat

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import adjust_permissions, copy_file

class EB_SAMtools(ConfigureMake):
    """
    Support for building SAMtools; SAM (Sequence Alignment/Map) format
    is a generic format for storing large nucleotide sequence alignments.
    """

    def __init__(self, *args, **kwargs):
        """Define lists of files to install."""
        super(EB_SAMtools, self).__init__(*args, **kwargs)

        self.bin_files = ["misc/blast2sam.pl",
                          "misc/bowtie2sam.pl", "misc/export2sam.pl", "misc/interpolate_sam.pl",
                          "misc/novo2sam.pl", "misc/psl2sam.pl", "misc/sam2vcf.pl", "misc/samtools.pl",
                          "misc/soap2sam.pl", "misc/varfilter.py", "misc/wgsim_eval.pl",
                          "misc/zoom2sam.pl", "misc/md5sum-lite", "misc/md5fa", "misc/maq2sam-short",
                          "misc/maq2sam-long", "misc/wgsim", "samtools"]

        self.include_files = ["bam.h", "bam2bcf.h", "bam_endian.h", "errmod.h",
                              "kprobaln.h",  "sam.h", "sam_header.h", "sample.h"]

        if LooseVersion(self.version) <= LooseVersion('0.1.18'):
            # seqtk is no longer there in v0.1.19
            self.bin_files += ["misc/seqtk"]
        elif LooseVersion(self.version) >= LooseVersion('0.1.19'):
            # new tools in v0.1.19
            self.bin_files += ["misc/ace2sam", "misc/r2plot.lua",
                               "misc/vcfutils.lua"]

        if LooseVersion(self.version) >= LooseVersion('0.1.19') and LooseVersion(self.version) < LooseVersion('1.0'):
            self.bin_files += ["misc/bamcheck", "misc/plot-bamcheck"]

        if LooseVersion(self.version) < LooseVersion('1.0'):
            self.bin_files += ["bcftools/vcfutils.pl", "bcftools/bcftools"]
            self.include_files += [ "bgzf.h", "faidx.h",  "khash.h", "klist.h", "knetfile.h", "razf.h",
                                    "kseq.h", "ksort.h", "kstring.h"]
        elif LooseVersion(self.version) >= LooseVersion('1.0'):
            self.bin_files += ["misc/plot-bamstats","misc/seq_cache_populate.pl"]

        if LooseVersion(self.version) < LooseVersion('1.2'):
            # kaln aligner removed in 1.2 (commit 19c9f6)
            self.include_files += ["kaln.h"]

        self.lib_files = ["libbam.a"]

    def configure_step(self):
        """Ensure correct compiler command & flags are used via arguments to 'make' build command"""
        for var in ['CC', 'CXX', 'CFLAGS', 'CXXFLAGS']:
            if var in os.environ:
                self.cfg.update('buildopts', '%s="%s"' % (var, os.getenv(var)))

        # configuring with --prefix only supported with v1.3 and more recent
        if LooseVersion(self.version) >= LooseVersion('1.3'):
            super(EB_SAMtools, self).configure_step()

    def install_step(self):
        """
        Install by copying files to install dir
        """
        install_files = [
            ('include/bam', self.include_files),
            ('lib', self.lib_files),
        ]

        # v1.3 and more recent supports 'make install', but this only installs (some of) the binaries...
        if LooseVersion(self.version) >= LooseVersion('1.3'):
            super(EB_SAMtools, self).install_step()

            # figure out which bin files are missing, and try copying them
            missing_bin_files = []
            for binfile in self.bin_files:
                if not os.path.exists(os.path.join(self.installdir, 'bin', os.path.basename(binfile))):
                    missing_bin_files.append(binfile)
            install_files.append(('bin', missing_bin_files))

        else:
            # copy binaries manually for older versions
            install_files.append(('bin', self.bin_files))

        self.log.debug("Installing files by copying them 'manually': %s", install_files)
        for (destdir, files) in install_files:
            for fn in files:
                dest = os.path.join(self.installdir, destdir, os.path.basename(fn))
                copy_file(os.path.join(self.cfg['start_dir'], fn), dest)

            # enable r-x permissions for group/others
            perms = stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH
            adjust_permissions(self.installdir, perms, add=True, recursive=True)

    def sanity_check_step(self):
        """Custom sanity check for SAMtools."""
        custom_paths = {
            'files': [os.path.join('bin', os.path.basename(f)) for f in self.bin_files] +
                     [os.path.join('include', 'bam', f) for f in self.include_files] +
                     [os.path.join('lib', f) for f in self.lib_files],
            'dirs': []
        }
        super(EB_SAMtools, self).sanity_check_step(custom_paths=custom_paths)
