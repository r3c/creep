Creep README file
=================

Overview
--------

Creep is an incremental deploy tool, allowing delta update from a Git
repository or a regular directory into a FTP or SSH remote server. It allows
deployment of any application where files needed on remote servers (e.g.
production) match files in your repository, meaning it works well with pure
front-end websites using HTML/CSS/JS or server technologies like PHP.

Projects deployed through Creep should provide one or two configuration file(s):

- _environments_ file (mandatory) contains the different locations where files
  will be sent (e.g. integration servers, production servers, etc.), plus a few
  related configuration options.
- _modifiers_ file (optional) describes how to transform files before sending
  them (e.g. compile, minify, obfuscate, etc.).

Deployments are incremental and Creep keeps track of deployed snapshots on
all remote locations so that only changed files are send next time. This
tracking mechanism depends on the type of repository used, for exemple Creep
uses revision hashes when deploying from a Git repository to allow easy diffs.

Installing
----------

To install Creep, checkout repository somewhere and create a symbolic link in
your `$PATH` to main executable file `creep.py` (located in `src` directory).
While this is not mandatory (you can prefer to call Creep using full path to
`creep.py`) it's surely more convenient.

    $ cd creep
    $ sudo ln -s src/creep.py /usr/bin/creep
    $ creep -h # display help

Once Creep is installed go to your project folder and follow next section to
create a your first environments configuration file.

Environments
------------

Environments file mostly consists in a list of named locations pointing to the
servers you'll want to deploy your project to. They must be specified in a JSON
file named `.creep.envs` and located inside the directory which contains the
file you want to deploy. This directory will be used as the root for your
deployment, meaning that all files it contains will be deployed to remote
location, preserving the same hierarchical structure. You can use a
sub-directory inside your project as your deployment root (e.g. the `src` folder
in your Git repository) so you only deploy its content. You can also support
multiple deployment configurations for a single project by having more than one
environments files in different folders (e.g. one in your `src` folder to deploy
your executable code and another one in `assets` to deploy static files to
web servers).

Here is what an environments configuration file looks like:

    {
        "default": {
            "connection": "file:///../webdev/my-project"
        },
        "integration": {
            "connection": "ftp://me:password@my-dev-server/www-data"
        },
        "production": {
            "connection": "ssh://login@my-prod-server.com/www-data"
        }
    }

Each location (`default`, `integration` and `production` in this example) must
specify a connection string defining a protocol and optional address,
credentials and/or path. Creep can currently deploy through local file system,
FTP or SSH, and some extra options may be specified depending on the protocol
; see below for details about protocols and options.

Once environments configuration file is ready you can start using Creep. Just
type `creep <env>` (or full path to `creep.py` if you didn't add it to your
`$PATH`) where `<env>` is remote location name. When not specified, location
`default` is used:

    $ creep

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
        "default": {
            "connection": "ssh://www-data@localhost/www.mywebsite.com/",
            "options": {
                "extra": "-o StrictHostKeyChecking=no"
            }
        }
    }

Here are the supported protocols, expected connection string and available
options for each of them:

- Local file system:
  - Use `file:///path` where path is relative to current directory.
  - Note the use of triple slash `///` because file protocol has no hostname.
- FTP:
  - Use `ftp://user:pass@host:port/path` where `user` and `pass` are optional
    credentials (anonymous login will be used if they're missing), `port` is an
    optional FTP port which defaults to 21, and `path` is a path relative to FTP
    user home directory.
  - Boolean option "passive" enables (default) or disables passive mode.
- SSH:
  - Use `ssh://user@host:port/path` where variables are similar to the ones used
    for FTP deployment. No password can be specified here, so you'll need to
    either enter password manually or setup SSH keys and start SSH agent.
  - String option "extra" can be used to pass additional parameters to SSH
    command, as shown in example above.

For all protocols path is relative by default. Start your path by a slash `/`
character to specify an absolute path, e.g. `file:////var/opt/myproject`. 

Modifiers
---------

Modifiers allow you to declare special behaviors that should be triggered on
some files before they're send to remote location. Creep supports three
different kinds of modifiers:

- _name_ modifiers can change the name of a file using regular expression
  search/replace ;
- _adapt_ modifiers can change the content of a file using a custom shell
  command ;
- _link_ modifiers can link one or more files together so they're evaluated
  when their parent file is changed.

Modifiers must be specified in a JSON file named `.creep.mods` located in the
same folder(s) than your environments configuration file(s). Each file specifies
a list of rules which apply to all files matching a given regular expression and
contain optional _name_, _adapt_ or _link_ modifiers.

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
            "modify": "lessc --clean-css '{}'",
            "link": "find . -name '*.less' | xargs grep -Fl \"$(basename '{}')\" || true",
            "rename": "\\1.css"
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

Troubleshooting
---------------

This project is still under develpement and may not behave as you would expect.
The `-v` (verbose) switch may help you understanding how your environments and
modifiers files are used in case of issue.

If you really can't figure out what's happening, don't hesitate to contact me!
