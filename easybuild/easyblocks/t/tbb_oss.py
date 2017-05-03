import glob
import os
import shutil
import commands
from distutils.version import LooseVersion

from easybuild.easyblocks.generic.intelbase import INSTALL_MODE_NAME_2015, INSTALL_MODE_2015
from easybuild.easyblocks.generic.intelbase import IntelBase, ACTIVATION_NAME_2012, LICENSE_FILE_NAME_2012
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_version
from easybuild.tools.systemtools import get_gcc_version, get_platform_name

from easybuild.easyblocks.generic.configuremake import ConfigureMake


class EB_tbb(ConfigureMake):
    """EasyBlock for tbb, threading building blocks"""

    def make_module_extra(self):

        os.chdir(self.installdir)
        library_folder = commands.getoutput('readlink -f build/*_release')
        #print library_folder
        #os.system('pwd')
        #os.system('ls build/')

        txt = super(EB_tbb, self).make_module_extra()
        txt += self.module_generator.set_environment('TBBROOT', self.installdir)
        txt += self.module_generator.set_environment('tbb_bin', library_folder)
        txt += self.module_generator.set_environment('LD_LIBRARY_PATH', library_folder)
        txt += self.module_generator.set_environment('LIBRARY_PATH', library_folder)
        txt += self.module_generator.set_environment('CPATH', os.path.join(self.installdir, 'include'))
        return txt

