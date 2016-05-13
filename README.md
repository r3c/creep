Creep README file
=================

Overview
--------

Creep is an incremental deploy tool, allowing delta update from a Git
repository or a regular directory into a FTP or SSH remote server. It allows
deployment of any application where files needed on remote servers (e.g.
production) match files in your repository, meaning it works well with pure
front-end websites using HTML/CSS/JS or server technologies like PHP.

Deployments are always incremental, meaning Creep keeps track of deployed files
on all remote locations so that only changed files are send next time. This
tracking mechanism depends on the type of directory used, for exemple Creep uses
revision hashes when deploying from a Git repository.

Installing
----------

You can install Creep using either pip or manual install from sources. If you
choose to use pip, just type the following:

    $ sudo pip install creep
    $ creep -h # display help to ensure install worked properly

If you prefer install Creep manually, checkout the Git repository somewhere and
create a symbolic link in your `$PATH` to main executable file `creep.py`
(located in `src` directory). While this is not mandatory (you can prefer to
call Creep using full path to `creep.py`) it's surely more convenient:

    $ git clone https://github.com/r3c/creep.git
    $ cd creep
    $ sudo ln -s src/creep.py /usr/bin/creep
    $ creep -h # display help

Once Creep is installed, go to your project folder and follow next section to
quickly create a basic configuration and deploy your first project.

Quick start
-----------

First go to the directory you want to deploy, e.g. the `src` folder of some
project. It can be located inside a Git repository or just be a regular folder,
Creep should detect it and use a suitable default configuration. Create a new
`.creep.envs` file inside this directory with following JSON content:

    {
        "locations": {
            "default": {
                "connection": "file:////tmp/creep-quickstart"
            }
        }
    }

Mind the quadruple slash in `file:////tmp/creep-quickstart` string. Once file is
saved go back into directory and execute creep with no parameter:

    $ creep

Creep should tell you about deploying this project for the first time and will
ask you to confirm, enter `Y` to continue. It will then display the full list
of files in your project (by scanning file system or browsing Git history
depending on the type of folder you were in), then ask you again to confirm.
Enter `Y` again and your project will be deployed to directory
`/tmp/creep-quickstart`.

For now "deployment" actually means "copy", since our configuration specifies a
local deployment directory. This deployment also was a full copy of all files in
the project rather than an incremental deployment because we were doing it for
the first time.

Now if you try to execute creep again you'll see a message saying no action is
required, since deployment folder already contains an up-to-date version of your
project. Now modify some file (and `git commit` them if you were using Git),
then execute the command again. This time Creep will try to send only the file
you changed rather than the full project.

This basic example shows how to incrementally deploy a project to some local
directory. In next sections we'll see how to deploy to remote locations (through
FTP or SSH) and register multiple deployment locations.

Environments
------------

As seen in quick start section, Creep reads deployment target(s) from a
configuration file called _environments_ file. It contains one or more named
location(s) pointing on servers your files should be deployed to. This file
should be named `.creep.envs` and be located inside the base directory of your
deployment configuration, meaning that all files it contains will be deployed to
remote location(s) preserving the same hierarchical structure. You can use a
sub-directory inside your project as your deployment root (e.g. the `src` folder
in your Git repository) so you only deploy its content. You can also support
multiple deployment configurations for a single project by having more than one
environments files in different folders (e.g. one in your `src` folder to deploy
your executable code and another one in `assets` to deploy static files to
web servers).

Here an example of environments configuration file showing most features:

    {
        "locations": {
            "default": {
                "connection": "file:///../webdev/my-project"
            },
            "integration": {
                "connection": "ftp://me:password@my-dev-server/www-data"
            },
            "production": {
                "connection": "ssh://login@my-prod-server.com/www-data"
            }
        },
        "source": "delta",
        "options": {
            "algorithm": "md5",
            "follow": false
        }
    }

- The `locations` part specifies available deployment locations. Each one must
  contain at least a `connection` string with protocol and optional address,
  credentials and/or path. Read details below for more information about
  supported protocols.
- The `source` part specifies how Creep should analyze differences when you
  execute it inside this directory. When this option is not specified Creep will
  auto-detect it based on current environment.
- The `options` part specifies custom parameters depending on the type of source
  you selected.

Here is the list of supported sources and available options for each of them:

- Git:
  - Specify `git` source so local `git` executable is used to get diff between
    two revisions. When using this mode Creep relies on Git history and only
    needs to remember which revision has been deployed. It also allows you to
    manually specify the revision you want to deploy through command line
    argument.
  - No options are available for this source type.
- Hash:
  - Specify `hash` source to have Creep computing a hash of each file to detect
    differences. This mode has a higher overhead than Git since it has to save
    a value for each file rather than one unique revision, but can work with any
    regular folder.
  - String option `algorithm` selects the hashing algorithm to be used among
    sha1, sha256, sha512 or md5 (default).
  - Boolean option `follow` specifies whether symbolic links should be
    followed or ignored (default).

Once environments configuration file is ready you can start using Creep. Just
type `creep <env>` where `<env>` is name of a configured location. When no name
is specified location `default` is used.

Creep will then connect to remote location and try to retrieve information from
last deployment to compute incremental tasks. When you deploy for the first time
this information won't be available and Creep will ask you if a full deploy
should be performed instead. After each successful deployment it will save
information on remote location in a `.creep.revs` file.

While storing deployment information on remote location keeps related data
altogether and works even if you're not the only one performing deployments,
you may prefer to store them locally instead. In that case just add a new
`local` option with value `true` for all affected locations in your
`.creep.envs` file:

    {
        ...
            "integration": {
                "connection": "ftp://me:password@my-dev-server/www-data/",
                "local": true
            },
        ...
    }

You can specify additional options depending on the protocol you're using. To
specify options just add an "options" property containing required options as a
JSON object:

    {
        ...
            "default": {
                "connection": "ssh://www-data@localhost/www.mywebsite.com/",
                "options": {
                    "extra": "-o StrictHostKeyChecking=no"
                }
            },
        ...
    }

Here is the list of supported protocols, expected connection string format and
available options for each of them:

- Local file system:
  - Use connection format `file:///path` where path is relative to current
    directory.
  - Note the use of triple slash `///` because file protocol has no hostname.
- FTP:
  - Use connection format `ftp://user:pass@host:port/path` where `user` and
    `pass` are optional credentials (anonymous login will be used if they're
    missing), `port` is an optional FTP port which defaults to 21, and `path` is
    a path relative to FTP user home directory.
  - Boolean option `passive` enables (default) or disables passive mode.
- SSH:
  - Use connection format `ssh://user@host:port/path` where variables are
    similar to the ones used for FTP deployment. No password can be specified
    here, so you'll need to either enter password manually or setup SSH keys and
    start SSH agent.
  - String option `extra` can be used to pass additional parameters to SSH
    command, as shown in example above.

For all protocols path is relative by default. Start your path by a slash `/`
character to specify an absolute path, e.g. `file:////var/opt/myproject`. 

Modifiers
---------

Modifiers allow you to define special behaviors that should be triggered on
some files before they're send to remote location (e.g. rename, compile, minify,
obfuscate, etc.). Creep supports three different kinds of modifiers:

- _rename_ modifiers can replace the name of a file using regular expression ;
- _modify_ modifiers can update the content of a file using a shell command ;
- _link_ modifiers can link one or more files together so they're sent whenever
  the file they relate to is changed.

Modifiers must be specified in a JSON file named `.creep.mods` located in the
same folder(s) than your environments configuration file(s). Each file specifies
a list of rules which apply to all files matching a given regular expression and
contain optional _rename_, _modify_ or _link_ modifiers.

Here is what a modifiers configuration file looks like:

    [
        {
            "pattern": "\\.dist$",
            "filter": "false"
        },
        {
            "pattern": "\\.min\\.js$"
        },
        {
            "pattern": "\\.js$",
            "modify": "uglifyjs --compress --mangle -- '{}'"
        },
        {
            "pattern": "(.*)\\.less$",
            "rename": "\\1.css",
            "modify": "lessc --clean-css '{}'",
            "link": "find . -name '*.less' | xargs grep -Fl \"$(basename '{}')\" || true"
        }
    ]

Each rule must specify matched files using a regular expression in `pattern`
property (remember that backslashes must be escaped in JSON, hence the double
`\\` used in this file). Rules are evaluated in sequence and each file can only
match one single rule (evaluation stops after the first matched pattern). Other
(optional) actions are applied on files matching given pattern, if any.

- `rename` action specifies a new name for file and supports back references on
  the regular expression used in `pattern`.
  - In the example above, files ending with `.less` will have their extension
    changed to `.css`: the back reference `\\1` captured original file name
    without extension in associated pattern.
- `filter` specifies a shell command to be executed, where special `{}` token is
  replaced by an absolute path to the file being matched. If this command
  returns a non-zero result, file won't be sent to remote location.
  - In the example above, the `false` command is used to unconditionally exclude
    files with name ending with `.dist` from deployment.
- `modify` action specifies a shell command (similar to `filter` action).
  Standard output of this command will replace content of the file before it's
  sent to remote location.
  - In the example above, executable `uglifyjs` is called to minify JavaScript
    files (ending with `.js`).
  - Note presence of a rule which matches files with name ending with `.min.js`:
    it doesn't specify any action but prevents the `\.js$` rule from being
    triggered for files that are already minified.
- `link` action specifies a shell command similar to the `adapt` one but is
  expected to return a path (relative to deployment directory) to all files that
  should be sent whenever matched ones are matched.
  - In the example above, a command using `find` and `grep` is used to list all
    files referencing currently ones, so they're also sent to remote location
    whenever the file they reference is changed.
  - Note the regular expression could have been more specific, but the point is
    to be sure to include all changed files when deploying ; a few false
    positives will just cause harmless extra synchronizations.

If you don't create any modifiers file, a default configuration is used. This
configuration contains a single rule to always exclude environments file from
deployments.

Troubleshooting
---------------

This project is still under develpement and may not behave as you would expect.
The `-v` (verbose) switch may help you understanding how your environments and
modifiers files are used in case of issue.

If you really can't figure out what's happening, don't hesitate to create an
issue on GitHub or contact me directly!
