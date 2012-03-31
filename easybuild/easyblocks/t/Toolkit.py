from easybuild.framework.application import Application

class Toolkit(Application):
    """
    Compiler toolkit: generate module file only, nothing to make/install
    """
    def build(self):
        """
        Do almost nothing
        - just create an install directory?
        """
        self.gen_installdir()
        self.make_installdir()

    def makeModuleReq(self):
        return ''

    def sanityCheck(self):
        """
        As a toolkit doens't install anything really, this is always true
        """
        self.sanityCheckOK = True