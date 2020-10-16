This example uses Matlab 2018a and MATLAB-2018a.eb  
Steps to install Matlab:
* Install the appropriate Java install which requires manual download. See Java documentation for install.
* Matlab needs a "File Installation Key". There are a few options available:
   * Your Matlab license should have a "`File Installation Key`" in under "`Advanced Options`" in the "`Install and Activate`" tab of your "`License Center`".
     This will only install the products associated with this license.
   * If you need to install all of the toolboxes to support multiple licenses Mathworks can enable a "`All Product File Installation Key`".
     This will install all of the client products but will not install server products like MDCS.
     A second manual installation on top of the first will be required.
   * If you have a server product key, like MDCS, the "`File Installation Key`" may not install client products like Matlab Compilers.
     A second manual installation on top of the first will be required.
* Edit the easyconfig file (`MATLAB-2018a.eb`).
   * Update the version of Java to match the version installed in step 1.
   * Add the following three lines
   ```
   # This string could be really long
   key = 'XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX'
   license_server = '<IP or FQDN>'
   license_server_port = '<port>'
   ```
* Download both ISO files from Mathworks.
* Create the tar file needed for install.
   ```
   $ mkdir R2018a
   $ mount -o loop,ro R2018a_glnxa64_dvd1.iso /mnt/
   $ rsync -avHlP /mnt/ R2018a/
   $ umount /mnt
   $ mount -o loop,ro R2018a_glnxa64_dvd2.iso /mnt/
   $ rsync -avHlP /mnt/ R2018a/
   $ umount /mnt
   $ tar -zcvf /my/easybuild/download/path/matlab-2018a.tar.gz R2018a
   ```
* Install with EasyBuild
   ```
   $ eb MATLAB-2018a.eb -r
   ```
