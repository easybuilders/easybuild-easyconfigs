# This file is an EasyBuild recipy as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright (c) 2012 University of Luxembourg / LCSB
# Author::    Cedric Laczny <cedric.laczny@uni.lu>, Fotis Georgatos <fotis.georgatos@uni.lu>
# License::   MIT/GPL
# File::      $File$ 
# Date::      $Date$
"""
Easybuild support for building ncurses (SAM - Sequence Alignment/Map)
"""

from easybuild.easyblocks.generic.configuremake import ConfigureMake


class EB_ncurses(ConfigureMake):
    """
    Support for building ncurses; SAM (Sequence Alignment/Map) format
    is a generic format for storing large nucleotide sequence alignments.
    """

    def configure_step(self):
        """
        No configure
        """
        self.cfg.update('configopts', '--with-shared --enable-overwrite')
        super(EB_ncurses, self).configure_step()

    def sanity_check_step(self):
        """Custom sanity check for ncurses."""

        custom_paths = {
                        'files' : ['bin/%s' % x for x in ["captoinfo", "clear", "infocmp", "infotocap", "ncurses5-config",
                                                          "reset", "tabs", "tic", "toe", "tput", "tset"]] +
                                  ['lib/lib%s.a' % x for x in ["form", "form", "menu", "menu_g", "ncurses", "ncurses++",
                                                               "ncurses_g", "panel", "panel_g"]],
                        'dirs' : ['include']
                       }

        super(EB_ncurses, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """  
        Set correct CPLUS path.
        """
        guesses = super(EB_ncurses, self).make_module_req_guess()
        guesses.update({'CPLUS': ['include/ncurses']})  # will only be present without --enable-overwrite
        return guesses
