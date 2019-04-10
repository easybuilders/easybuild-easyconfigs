We'd love you to contribute back to EasyBuild, and here's how you can do it: the branch - hack - pull request cycle.


## Preparation

### Fork easybuild-easyconfigs

First, you'll need to fork [easybuild-easyconfigs on GitHub](https://github.com/easybuilders/easybuild-easyconfigs).

If you do not have a (free) GitHub account yet, you'll need to get one.

You should also register an SSH public key, so you can easily clone, push to and pull from your repository.

### Clone your easybuild-easyconfigs repository

Clone your fork of the easybuild-easyconfigs repository to your favorite workstation. 

```bash
git clone git@github.com:YOUR\_GITHUB\_LOGIN/easybuild-easyconfigs.git
```

### Pull in the develop branch

Pull the _develop_ branch from the main easybuild-easyconfigs repository:

```bash
cd easybuild
git remote add github_easybuilders git@github.com:easybuilders/easybuild-easyconfigs.git
git branch develop
git checkout develop
git pull github_easybuilders develop
```

### Keep develop up-to-date

The _develop_ branch hosts the latest bleeding-edge version of easybuild-easyconfigs, and is merged into _master_ regularly (after thorough testing). 

Make sure you update it every time you create a feature branch (see below):

```bash
git checkout develop
git pull github_easybuilders develop
```



## Branch

### Pick a branch name

Please try and follow these guidelines when picking a branch name:
 * use the number of the issue as a prefix for your branch name, e.g. `86_` for issue [#86](https://github.com/easybuilders/easybuild-framework/issues/86)
 * append a short but descriptive branch name, in which words are joined by underscores, e.g. `86_encoding_scheme`

### Create branch

Create a feature branch for your work, and check it out

```bash
git checkout develop
git branch <BRANCH_NAME>
git checkout <BRANCH_NAME>
```

Make sure to always base your features branches on _develop_, not on _master_!

 

## Hack

After creating the branch, implement your contributions: new features, new easyblocks for non-supported software, enhancements or updates to existing easyblocks, bug fixes, or rewriting the whole thing in Fortran, whatever you like.

Make sure you commit your work, and try to do it in bite-size chunks, so the commit log remains clear.

For example:

```bash
git add easybuild/easyblocks/l/linuxfromscratch.py
git commit -m "support for Linux From Scratch"
```

If you are working on several things at the same time, try and keep things isolated in seperate branches, to keep it manageable (both for you, and for reviewing your contributions, see below).



## Pull request

When you've finished the implementation of a particular contribution, here's how to get it into the main easybuild-easyconfigs repository (also see https://help.github.com/articles/using-pull-requests/)

### Push your branch

Push your branch to your easybuild-easyconfigs repository on GitHub:
 
```bash
git push origin <BRANCH_NAME>
```


### Issue a pull request

Issue a pull request for your branch into the main easybuild-easyconfigs repository, as follows:

 * go to github.com/YOUR\_GITHUB\_LOGIN/easybuild-easyconfigs, and make sure the branch you just pushed is selected (not _master_, but _<BRANCH_NAME>_)

 * issue a pull request (see button at the top of the page) for your branch to the **_develop_** branch of the main easybuild-easyconfigs repository; **note**: don't issue a pull request to the _master_ branch, as it will be simply closed by the EasyBuild team

 * make sure to reference the corresponding issue number in the pull request, using the notation # followed by a number, e.g. `#83`

### Issue pull request for existing ticket (from command line)

If you're contributing code to an existing issue you can also convert the issue to a pull request by running
``` 
GITHUBUSER=your_username && PASSWD=your_password && BRANCH=branch_name && ISSUE=issue_number && \
curl --user "$GITHUBUSER:$PASSWD" --request POST \
--data "{\"issue\": \"$ISSUE\", \"head\": \"$GITHUBUSER:$BRANCH\", \"base\": \"develop\"}" \
https://api.github.com/repos/easybuilders/easybuild-easyconfigs/pulls
```
This is currently only supported by github from the command line and not via the web interface.
You might also want to look into [hub](https://github.com/defunkt/hub) for more command line features.

### Review process

A member of the EasyBuild team will then review your pull request, paying attention to what you're contributing, how you implemented it and [code style](http://easybuild.readthedocs.org/en/latest/Code_style.html).

Most likely, some remarks will be made on your pull request. Note that this is nothing personal, we're just trying to keep the EasyBuild codebase as high quality as possible. Even when an EasyBuild team member makes changes, the same public review process is followed.

Try and act on the remarks made, either by commiting additional changes to your branch, or by replying to the remarks to clarify your work.


### Aftermath

Once your pull request has been reviewed and remarks have been processed, your contribution will be merged into the _develop_ branch of the main easybuild-easyconfigs repository.

On frequent occasions, the _develop_ branch is merged into the _master_ branch and a new version is tagged, and your contribution truly becomes part of EasyBuild.
