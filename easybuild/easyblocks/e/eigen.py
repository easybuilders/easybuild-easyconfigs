# This file is an EasyBuild recipy as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright (c) 2012 University of Luxembourg / LCSB
# Author::    Cedric Laczny <cedric.laczny@uni.lu>, Fotis Georgatos <fotis.georgatos@uni.lu>
# License::   MIT/GPL
# File::      $File$ 
# Date::      $Date$

"""
EasyBuild support for building and installing Eigen, implemented as an easyblock
"""

import os
import shutil
from easybuild.framework.application import Application

class EB_Eigen(Application):
    """
    Support for building Eigen (Eigen is a C++ template library for linear algebra: matrices, vectors, numerical solvers, and related algorithms.)
    """

    def configure(self):
        """
        EMPTY
        """
        pass

    def make(self):
        """
        EMPTY
        """
        pass

    def make_install(self):
        """
        Install by copying files to install dir
        """
        srcdir = self.getcfg('startfrom')
        srcdir = os.path.join(srcdir, 'Eigen')
        destdir = os.path.join(self.installdir, 'include/Eigen')
        srcfile = None
        try:
                shutil.copytree(srcdir, destdir)
        except OSError, err:
            self.log.exception("Copying %s to installation dir %s failed: %s" % (srcfile, destdir, err))

    def make_module_req_guess(self):
        """  
        A dictionary of possible directories to look for.
        Include CPLUS_INCLUDE_PATH as an addition to default ones
        Removed unnecessary stuff
        """
        return {
            'CPLUS_INCLUDE_PATH': ['include'],
            'LD_LIBRARY_PATH': ['lib', 'lib64'],
        }
