In order to use these configs you must first download the Intel Parallel Studio XE CPP file. NOT the full bundle! The file should look like this: parallel_studio_xe_2018_update2_composer_edition_for_cpp.tgz    

Next you must specify the license file. There are three options:  
* Place it in the following path: ~/licenses/intel/license.lic
* Set an environment variable: `export INTEL_LICENSE_FILE=/path/to/file.lic`
* Set an environment variable: `export LM_LICENSE_FILE=/path/to/file.lic`

To install, you must configure EasyBuild to use the right `sourcepath` so it can find the manually downloaded file. There are a number of ways to do this assuming the file is in /home/username/EB_Downloads.  
* Pass it as a option on the command line: `eb icc-2018.2.199-GCC-6.4.0-2.28.eb -r --sourcepath=/home/username/EB_Downloads`  
* Set an environment variable: `export EASYBUILD_SOURCEPATH=/home/username/EB_Downloads ; eb icc-2018.2.199-GCC-6.4.0-2.28.eb -r`  
* Configure a permanent location in ~/.config/easybuild/config.cfg before installing with `eb icc-2018.2.199-GCC-6.4.0-2.28.eb -r`
> [config]  
> sourcepath=/home/username/EB_Downloads
