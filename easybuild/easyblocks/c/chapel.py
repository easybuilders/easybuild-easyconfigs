## 
# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2012-2016 Uni.Lu/LCSB, NTUA
# Authors::   Fotis Georgatos <fotis@cern.ch>, Kenneth Hoste
# License::   MIT/GPL
# $Id$
#
# This work implements a part of the HPCBIOS project and is a component of the policy:
# http://hpcbios.readthedocs.org/en/latest/
##
"""
EasyBuild support for Chapel, implemented as an easyblock

@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
"""
import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake


class EB_Chapel(ConfigureMake):
    """Support for building Chapel."""

    def __init__(self, *args, **kwargs):
        """Initialize Chapel-specific variables."""
        super(EB_Chapel, self).__init__(*args, **kwargs)
        self.build_in_installdir = True

    def configure_step(self):
        """No configure step for Chapel."""
        pass

    # building is done via make, so taken care of by ConfigureMake easyblock

    def install_step(self):
        """Installation of Chapel has already been done as part of the build procedure"""
        pass

    def sanity_check_step(self):
        """Custom sanity check for Chapel."""

        libpath = os.path.join('lib', 'linux64', 'gnu', 'comm-none', 'substrate-none', 'seg-none',
                               'mem-default', 'tasks-fifo', 'threads-pthreads', 'atomics-intrinsics')
        custom_paths = {
                        'files': ['bin/linux64/chpl', 'bin/linux64/chpldoc',
                                  os.path.join(libpath, 'libchpl.a'), os.path.join(libpath, 'main.o')],
                        'dirs': []
                       }

        super(EB_Chapel, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for; this is needed since bin/linux64 of chapel is non standard
        """
        return {
                'PATH': ['bin', 'bin/linux64', 'bin64'],
                'LD_LIBRARY_PATH': ['lib', 'lib/linux64', 'lib64'],
               }

