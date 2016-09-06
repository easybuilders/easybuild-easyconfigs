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
EasyBuild support for building and installing Cufflinks, implemented as an easyblock

@author: Cedric Laczny (Uni.Lu)
@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
"""
import fileinput
import glob
import re
import os
import sys

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root


class EB_Cufflinks(ConfigureMake):
    """
    Support for building and installing Cufflinks
    """

    def configure_step(self):
        """
        Check for dependencies
        """
        for dep in ['Boost', 'Eigen', 'SAMtools']:
            if not get_software_root(dep):
                raise EasyBuildError("Dependency module %s not loaded?", dep)

        super(EB_Cufflinks, self).configure_step()

    def patch_step(self):
        """
        First we need to rename a few things, s.a. http://wiki.ci.uchicago.edu/Beagle/BuildingSoftware -> "Cufflinks"
        """
        build_dir = os.getcwd()
        source_files = build_dir + '/src/*.cpp'
        header_files = build_dir + '/src/*.h'
        files = glob.glob(source_files)
        files = files + (glob.glob(header_files))
        for fname in files:
            for line in fileinput.input(fname, inplace=1, backup='.orig'):
                line = re.sub(r'foreach', 'for_each', line, count=0)
                sys.stdout.write(line)

        for line in fileinput.input(os.path.join(build_dir, 'src', 'common.h'), inplace=1, backup='.orig'):
                line = re.sub(r'#include \<boost\/for\_each.hpp\>', '#include <boost/foreach.hpp>', line, count=0)
                sys.stdout.write(line)

        super(EB_Cufflinks, self).patch_step()
