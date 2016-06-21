import os
import shutil

from easybuild.easyblocks.generic.tarball import Tarball
from easybuild.tools.build_log import EasyBuildError


class EB_Gurobi(Tarball):
    """Support for installing linux64 version of Gurobi."""

    def configure_step(self):
        """No configuration for Gurobi."""
        # ensure a license file is specified
        if self.cfg['license_file'] is None:
            raise EasyBuildError("No license file specified.")

    def install_step(self):
        """Install Gurobi and license file."""

        super(EB_Gurobi, self).install_step()

        # copy license file
        lic_path = os.path.join(self.installdir, 'gurobi.lic')
        try:
            shutil.copy2(self.cfg['license_file'], lic_path)
        except OSError as err:
            raise EasyBuildError("Failed to copy license file to %s: %s", lic_path, err)

    def sanity_check_step(self):
        """Custom sanity check for Gurobi."""
        custom_paths = {
            'files': ['bin/%s' % f for f in ['grbprobe', 'grbtune', 'gurobi_cl', 'gurobi.sh']],
            'dirs': [],
        }
        super(EB_Gurobi, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Custom extra module file entries for Gurobi."""
        txt = super(EB_Gurobi, self).make_module_extra()

        txt += self.module_generator.set_environment('GUROBI_HOME', self.installdir)
        txt += self.module_generator.set_environment('GRB_LICENSE_FILE', os.path.join(self.installdir, 'gurobi.lic'))

        return txt

