#!/usr/bin/env python
#
#  Copyright (C) 2015 IT4Innovations
#  Lumir Jasiok
#  lumir.jasiok@vsb.cz
#  http://www.it4i.cz
#
#
#

"""
EasyBuild support for building and installing Intel Performance Primitives (IPP) library, implemented as an easyblock. 
@author: Lumir Jasiok (IT4Innovations)
"""

import os
import platform

from easybuild.easyblocks.generic.intelbase import IntelBase
from easybuild.tools.run import run_cmd

class EB_ipp(IntelBase):
    """
    Support for installing Intel Performance Primitives
    """

    def install_step(self):
        """Actual installation
        
        - create silent.cfg
        - run install.sh
        """
        
        machine = platform.machine()
        if machine == "i386":
            self.arch = "ia32"
        else:
            self.arch = "intel64"

        silent_cfg = """
ACCEPT_EULA=accept
CONTINUE_WITH_OPTIONAL_ERROR=yes
PSET_INSTALL_DIR=%s
CONTINUE_WITH_INSTALLDIR_OVERWRITE=yes
COMPONENTS=ALL
PSET_MODE=install
ACTIVATION_LICENSE_FILE=%s
ACTIVATION_TYPE=license_file
PHONEHOME_SEND_USAGE_DATA=no
SIGNING_ENABLED=yes
ARCH_SELECTED=%s
        """ % (self.installdir, self.license_file, self.arch.upper())
        build_dir = self.cfg['start_dir']
        silent_file = os.path.join(build_dir, 'silent.cfg')
        fd = open(silent_file, 'w')
        fd.write(silent_cfg)
        fd.close()

        os.chdir(build_dir)
        self.log.info("Build dir is %s" % (build_dir))
        cmd = "./install.sh -s silent.cfg --SHARED_INSTALL"
        run_cmd(cmd, log_all=True, simple=True)
        return True
    
    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for
        """
        guesses = super(EB_ipp, self).make_module_req_guess()

        lib_path = 'lib/%s' % self.arch 
        lib_arr = []
        lib_arr.append(lib_path)

        guesses.update({
            'LD_LIBRARY_PATH': lib_arr,
            'LIBRARY_PATH': lib_arr,
            'CPATH': ['ipp/include'],
            'INCLUDE': ['ipp/include'],
        })

        return guesses
