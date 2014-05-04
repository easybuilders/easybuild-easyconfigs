import os

from easybuild.easyblocks.generic.makecp import MakeCp
from easybuild.framework.easyconfig import BUILD, MANDATORY
from easybuild.tools.filetools import run_cmd

class EB_Go(MakeCp):
    def build_step(self, verbose=False):
        try:
             os.chdir("%s/src" % (self.cfg['start_dir']))
        except OSError, err:
             elf.log.error("Failed to move (back) to %s: %s" % (self.cfg['start_dir'], err))
        cmd = "GOROOT_FINAL=%s ./all.bash" % (self.installdir)
        (out, _) = run_cmd(cmd, log_all=True, simple=False, log_output=verbose)
        return out
