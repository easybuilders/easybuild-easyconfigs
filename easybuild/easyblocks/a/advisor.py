"""
EasyBuild support for installing the Intel Advisor XE, implemented as an easyblock

@author: Lumir Jasiok (IT4Innovations)
"""

from easybuild.easyblocks.generic.intelbase import IntelBase

class EB_Advisor(IntelBase):
    """
    Support for installing Intel Advisor XE
    """

    def sanity_check_step(self):
        """Custom sanity check paths for Advisor"""

        custom_paths = {
            'files': ["advisor_xe/lib64/libadvixe_runtool_6.6.so", "advisor_xe/lib64/libadvixe_dvt_core_6.5.so"],
            'dirs': ['advisor_xe/bin64', 'advisor_xe/lib64']
        }

        super(EB_Advisor, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for
        """
        guesses = super(EB_Advisor, self).make_module_req_guess()

        lib_path = 'advisor_xe/lib64'
        include_path = 'advisor_xe/include'
 
        guesses.update({
            'LD_LIBRARY_PATH': [lib_path],
            'LIBRARY_PATH': [lib_path],
            'CPATH': [include_path],
            'INCLUDE': [include_path],
            'PATH': ['advisor_xe/bin64'],
        })

        return guesses
