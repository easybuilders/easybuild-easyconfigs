"""
EasyBuild support for Boost on Cray, implemented as an easyblock

@author: Petar Forai (IMP/IMBA)
@author: Luca Marsella (CSCS)
@author: Guilherme Peretti-Pezzi (CSCS)
"""
import os
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.boost import EB_Boost
from easybuild.framework.easyblock import EasyBlock
#from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
#from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd
#from easybuild.tools.systemtools import get_glibc_version, UNKNOWN


class boostcray(EB_Boost):
    """Support for building Boost on cray."""

    def configure_step(self):
        """Configure Boost build using custom tools"""

        # mpi sanity check
        if self.cfg['boost_mpi'] and not self.toolchain.options.get('usempi', None):
            raise EasyBuildError("When enabling building boost_mpi, also enable the 'usempi' toolchain option.")

        # create build directory (Boost doesn't like being built in source dir)
        try:
            self.objdir = os.path.join(self.builddir, 'obj')
            os.mkdir(self.objdir)
            self.log.debug("Succesfully created directory %s" % self.objdir)
        except OSError, err:
            raise EasyBuildError("Failed to create directory %s: %s", self.objdir, err)

        # generate config depending on compiler used
        toolset = self.cfg['toolset']
        if toolset is None:
            if self.toolchain.comp_family() == toolchain.INTELCOMP:
                toolset = 'intel-linux'
            elif self.toolchain.comp_family() == toolchain.GCC:
                toolset = 'gcc'
            else:
                raise EasyBuildError("Unknown compiler used, don't know what to specify to --with-toolset, aborting.")

        cmd = "./bootstrap.sh --with-toolset=%s --prefix=%s %s" % (toolset, self.objdir, self.cfg['configopts'])
        run_cmd(cmd, log_all=True, simple=True)

        if self.cfg['boost_mpi']:

            self.toolchain.options['usempi'] = True
            # configure the boost mpi module
            # http://www.boost.org/doc/libs/1_47_0/doc/html/mpi/getting_started.html
            # let Boost.Build know to look here for the config file
            f = open('user-config.jam', 'a')
            self.log.info("PRGENV_MODULE_NAME_SUFFIX is %s " % (self.toolchain.PRGENV_MODULE_NAME_SUFFIX))
#	    self.log.info("TC_CONSTANT_CRAYPE is %s " % (self.toolchain.TC_CONSTANT_CRAYPE))
            #if self.toolchain.TC_CONSTANT_CRAYPE in [toolchain.CRAYPE+'_GNU', toolchain.CRAYPE+'_Intel'] :
            if self.toolchain.PRGENV_MODULE_NAME_SUFFIX in ['gnu', 'intel'] :
                craympichdir=os.getenv('CRAY_MPICH2_DIR')
                craygccversion=os.getenv('GCC_VERSION')
		f = open('user-config.jam','a')
		config = '\n'.join([	
                'import os ; ',
                'local CRAY_MPICH2_DIR =  %s ;' %(craympichdir),
                'using gcc ',
		': %s' %(craygccversion),
                ': CC ',
                ': <compileflags>-I$(CRAY_MPICH2_DIR)/include ',
                '  <linkflags>-L$(CRAY_MPICH2_DIR)/lib \ ',
                '; ',
                'using mpi ',
                ': CC ',
                ': <find-shared-library>mpich ',
                ': aprun -n \ ',
                ';',
		'',
		])
		f.write(config)
	    else:
	        f.write("using mpi : %s ;" % os.getenv("MPICXX"))

	    f.close()
