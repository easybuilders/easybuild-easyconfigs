## 
# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2012-2013 The Cyprus Institute
# Authors::   George Tsouloupas <g.tsouloupas@cyi.ac.cy>, Andreas Panteli <a.panteli@cyi.ac.cy>
# License::   MIT/GPL
# $Id$
#
##
"""
EasyBuild support for building and installing MUSCLE, implemented as an easyblock

@author: George Tsouloupas (CyI)
@author: Andreas Panteli (CyI)
"""

import os

from easybuild.framework.easyblock import EasyBlock
from easybuild.easyblocks.generic.packedbinary import PackedBinary
from easybuild.tools.filetools import mkdir, extract_file


class EB_MUSCLE(PackedBinary):
    """
    Support for building MUSCLE

    """
    def extract_step(self):
        """
        Unpack the source files.
        """

        newdir = '%s-%s' % (self.name.lower(), self.version)
        self.cfg['start_dir'] = os.path.join(self.builddir, newdir)
        try:
            mkdir(self.cfg['start_dir'])
            self.log.debug("Created new directory %s" % (self.cfg['start_dir']))
        except OSError, err:
            self.log.exception("Can't create new directory %s: %s" % (self.cfg['start_dir'], err))
        for tmp in self.src:
            self.log.info("Unpacking source %s" % tmp['name'])
            srcdir = extract_file(tmp['path'], self.cfg['start_dir'], cmd=tmp['cmd'], extra_options=self.cfg['unpack_options'])
            if srcdir:
                self.src[self.src.index(tmp)]['finalpath'] = srcdir
            else:
                self.log.error("Unpacking source %s failed" % tmp['name'])    
