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
EasyBuild support for building and installing Bowtie2, implemented as an easyblock

@author: Cedric Laczny (Uni.Lu)
@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
"""
from distutils.version import LooseVersion
import os

from easybuild.easyblocks.generic.makecp import MakeCp
from easybuild.framework.easyconfig import CUSTOM


class EB_Bowtie2(MakeCp):
    """
    Support for building bowtie2 (ifast and sensitive read alignment)
    - create Make.UNKNOWN
    - build with make and install 
    """
    @staticmethod
    def extra_options(extra_vars=None):
        """Change default values of options"""
        extra = MakeCp.extra_options()
        # files_to_copy is not mandatory here
        extra['files_to_copy'][2] = CUSTOM
        return extra

    def __init__(self, *args, **kwargs):
        """Bowtie2 easyblock constructor, define class variables."""
        super(EB_Bowtie2, self).__init__(*args, **kwargs)

        self.bowtie2_files = ['bowtie2', 'bowtie2-build', 'bowtie2-inspect', 'MANUAL', 'MANUAL.markdown', 'NEWS']
        if LooseVersion(self.version) >= LooseVersion('2.2.0'):
            self.bowtie2_files.extend(['bowtie2-align-l', 'bowtie2-align-s', 'bowtie2-build-l', 'bowtie2-build-s',
                                       'bowtie2-inspect-l', 'bowtie2-inspect-s'])
        else:
            self.bowtie2_files.extend(['bowtie2-align'])

        if LooseVersion(self.version) >= LooseVersion('2.0.5'):
            self.bowtie2_files.append('LICENSE')

    def configure_step(self):
        """No custom configuration step for Bowtie2"""
        pass

    def build_step(self):
        """Build Bowtie2, make sure right compilation flags are used"""

        cc = os.getenv('CC')
        if cc:
            self.cfg.update('buildopts', 'CC="%s"' % cc)

        cxx = os.getenv('CXX')
        if cxx:
            self.cfg.update('buildopts', 'CPP="%s" CXX="%s"' % (cxx, cxx))

        cxxflags = os.getenv('CXXFLAGS')
        if cxxflags:
            self.cfg.update('buildopts', 'RELEASE_FLAGS="%s"' % cxxflags)

        super(EB_Bowtie2, self).build_step()

    def install_step(self):
        """
        Install by copying files to install dir
        """
        self.cfg['files_to_copy'] = [(self.bowtie2_files, 'bin'), 'doc', 'example', 'scripts']
        super(EB_Bowtie2, self).install_step()

    def sanity_check_step(self):
        """Custom sanity check for Bowtie2."""
        custom_paths = {
            'files': [os.path.join('bin', f) for f in self.bowtie2_files],
            'dirs': ['doc', 'example', 'scripts']
        }
        super(EB_Bowtie2, self).sanity_check_step(custom_paths=custom_paths)
