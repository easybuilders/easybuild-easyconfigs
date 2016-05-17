##
# Copyright 2015-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""
EasyBuild support for building and installing OCaml + opam (+ extensions), implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


EXTS_FILTER_OCAML_PACKAGES = ("eval `opam config env` && opam list --installed %(ext_name)s.%(ext_version)s", '')
OPAM_SUBDIR = 'opam'


class EB_OCaml(ConfigureMake):
    """Support for building/installing OCaml + opam (+ additional extensions)."""

    def __init__(self, *args, **kwargs):
        """Initialisation of custom class variables for OCaml."""
        super(EB_OCaml, self).__init__(*args, **kwargs)
        self.with_opam = False

    def configure_step(self):
        """Custom configuration procedure for OCaml."""
        self.cfg['prefix_opt'] = '-prefix '
        self.cfg.update('configopts', '-cc "%s %s"' % (os.environ['CC'], os.environ['CFLAGS']))

        if not 'world.opt' in self.cfg['buildopts']:
            self.cfg.update('buildopts', 'world.opt')

        super(EB_OCaml, self).configure_step()

    def install_step(self):
        """
        Custom install procedure for OCaml.
        First install OCaml using 'make install', then install OPAM (if sources are provided).
        """
        super(EB_OCaml, self).install_step()

        fake_mod_data = self.load_fake_module(purge=True)

        try:
            all_dirs = os.listdir(self.builddir)
        except OSError, err:
            raise EasyBuildError("Failed to check contents of %s: %s", self.builddir, err)

        opam_dirs = [d for d in all_dirs if d.startswith('opam')]
        if len(opam_dirs) == 1:
            opam_dir = os.path.join(self.builddir, opam_dirs[0])
            self.log.info("Found unpacked OPAM sources at %s, so installing it.", opam_dir)
            self.with_opam = True
            try:
                os.chdir(opam_dir)
            except OSError, err:
                raise EasyBuildError("Failed to move to %s: %s", opam_dir, err)

            run_cmd("./configure --prefix=%s" % self.installdir)
            run_cmd("make lib-ext")  # locally build/install required dependencies
            run_cmd("make")
            run_cmd("make install")
            run_cmd("opam init --root %s" % os.path.join(self.installdir, OPAM_SUBDIR))
        else:
            self.log.warning("OPAM sources not found in %s: %s", self.builddir, all_dirs)

        self.clean_up_fake_module(fake_mod_data)

    def prepare_for_extensions(self):
        """Set default class and filter for OCaml packages."""
        # build and install additional packages with OCamlPackage easyblock
        self.cfg['exts_defaultclass'] = "OCamlPackage"
        self.cfg['exts_filter'] = EXTS_FILTER_OCAML_PACKAGES
        super(EB_OCaml, self).prepare_for_extensions()

    def fetch_extension_sources(self):
        """Don't fetch extension sources, OPAM takes care of that (and archiving too)."""
        return [{'name': ext_name, 'version': ext_version} for ext_name, ext_version in self.cfg['exts_list']]

    def sanity_check_step(self):
        """Custom sanity check for OCaml."""
        binaries = ['bin/ocaml', 'bin/ocamlc', 'bin/ocamlopt', 'bin/ocamlrun']
        dirs = []
        if self.with_opam:
            binaries.append('bin/opam')
            dirs.append(OPAM_SUBDIR)

        custom_paths = {
            'files': binaries,
            'dirs': dirs,
        }

        super(EB_OCaml, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Custom extra paths/variables to define in generated module for OCaml."""
        guesses = super(EB_OCaml, self).make_module_req_guess()

        guesses.update({
            'CAML_LD_LIBRARY_PATH': ['lib'],
            'OPAMROOT': [OPAM_SUBDIR],
            'PATH': ['bin', os.path.join(OPAM_SUBDIR, 'system', 'bin')],
        })

        return guesses
