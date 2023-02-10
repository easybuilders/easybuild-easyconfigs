In order to use these configs you must first download Java from [Oracle](http://www.oracle.com/technetwork/java/javase/downloads/index.html). The file name should look like this: jdk-8u162-linux-x64.tar.gz    

To install, you must configure EasyBuild to use the right `sourcepath` so it can find the manually downloaded file. There are a number of ways to do this assuming the file is in /home/username/EB_Downloads.  
* Pass it as a option on the command line: `eb Java-1.8.0_162.eb -r --sourcepath=/home/username/EB_Downloads`  
* Set an environment variable:`export EASYBUILD_SOURCEPATH=/home/username/EB_Downloads ; eb Java-1.8.0_162.eb -r`  
* Configure a permanent location in ~/.config/easybuild/config.cfg before installing with `eb Java-1.8.0_162.eb -r`
> [config]  
> sourcepath=/home/username/EB_Downloads
