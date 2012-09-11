## FG MIT/GPL
"""
EasyBuild support for PAPI, implemented as an easyblock
"""
import os

from easybuild.framework.application import Application


class EB_PAPI(Application):
    """
    Support for building PAPI.
    Configure and build in installation dir.
    """

    def __init__(self, *args, **kwargs):
        """Custom initialization for PAPI: specify to start from 'src'."""

        Application.__init__(self, *args, **kwargs)

        self.setcfg('startfrom', 'src')

