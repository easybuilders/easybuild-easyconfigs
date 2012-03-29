import os
from easybuild.framework.application import Application

class MVAPICH2(Application):
    """
    Support for building the MVAPICH2 MPI library.
    - some compiler dependent configure options
    """

    def __init__(self, *args, **kwargs):
        Application.__init__(self, *args, **kwargs)

        self.cfg.update({
                         'withchkpt':[False, "Enable checkpointing support (required BLCR) (default: False)"],
                         'withlimic2':[False, "Enable LiMIC2 support for intra-node communication (default: False)"],
                         'withmpe':[False, "Build MPE routines (default: False)"],
                         'debug':[False, "Enable debug build (which is slower) (default: False)"],
                         'rdma_type':["gen2", "Specify the RDMA type (gen2/udapl) (default: gen2)"]
                         })

    def configure(self):

        # additional configuration options
        add_configopts = '--with-rdma=%s ' % self.getcfg('rdma_type')

        # use POSIX threads
        add_configopts += '--with-thread-package=pthreads '

        if self.getcfg('debug'):
            # debug build, with error checking, timing and debug info
            # note: this will affact performance
            add_configopts += '--enable-fast=none '
        else:
            # optimized build, no error checking, timing or debug info
            add_configopts += '--enable-fast '

        # enable shared libraries, using GCC and GNU ld options
        add_configopts += '--enable-shared --enable-sharedlibs=gcc '

        # enable Fortran 77/90 and C++ bindings
        add_configopts += '--enable-f77 --enable-fc --enable-cxx '

        # MVAPICH configure script complains when F90 or F90FLAGS are set, 
        # they should be replaced with FC/FCFLAGS instead
        for (envvar, new_envvar) in [("F90", "FC"), ("F90FLAGS", "FCFLAGS")]:
            envvar_val = os.getenv(envvar)
            if envvar_val:
                if not os.getenv(new_envvar):
                    os.putenv(new_envvar, envvar_val)
                    os.putenv(envvar, '')
                else:
                    self.log.error("Both %(ev)s and %(nev)s set, can I overwrite %(nev)s with %(ev)s (%(evv)s) ?" % {
                                                                                                                   'ev':envvar,
                                                                                                                   'nev':new_envvar,
                                                                                                                   'evv':envvar_val
                                                                                                                   })

        # enable specific support options (if desired)
        if self.getcfg('withmpe'):
            add_configopts += '--enable-mpe '
        if self.getcfg('withlimic2'):
            add_configopts += '--enable-limic2 '
        if self.getcfg('withchkpt'):
            add_configopts += '--enable-checkpointing --with-hydra-ckpointlib=blcr '

        self.updatecfg('configopts', add_configopts)

        Application.configure(self)

    # make and make install are default