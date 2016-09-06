##
# This file is an EasyBuild reciPY as per https://github.com/hpcugent/easybuild
#
# Copyright:: Copyright 2012-2016 Uni.Lu/LCSB, NTUA
# Authors::   Cedric Laczny <cedric.laczny@uni.lu>, Fotis Georgatos <fotis@cern.ch>, Kenneth Hoste
# License::   MIT/GPL
# $Id$
#
# This work implements a part of the HPCBIOS project and is a component of the policy:
# http://hpcbios.readthedocs.org/en/latest/HPCBIOS_2012-90.html
##
"""
Easybuild support for building ncurses, implemented as an easyblock

@author: Cedric Laczny (Uni.Lu)
@author: Fotis Georgatos (Uni.Lu)
@author: Kenneth Hoste (Ghent University)
"""

from easybuild.easyblocks.generic.configuremake import ConfigureMake

class EB_ncurses(ConfigureMake):
    """
    Support for building ncurses
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
