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

	$ pip install creep
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
`.creep.env` file inside this directory with following JSON content:

	{
		"default": {
			"connection": "file:////tmp/creep-quickstart"
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

Environment file
----------------

As seen in quick start section Creep reads deployment location(s) from a
configuration file called _environment_ file. It contains one or more named
location(s) pointing on servers your files should be deployed to. This file
should be named `.creep.env` and be located in any directory you want to deploy.

Creep will recursively deploy contents of the directory where your environment
file is to remote location(s), preserving the same hierarchical structure. You
can have several environment files in several sub-directories inside your
projet, e.g. one in `src` directory to deploy executable code and another one in
`assets` directory to deploy static files to web servers.

Environment configuration file uses JSON format and looks like this:

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

Elements in the root object specifies an available deployment location. Each one
must contain at least a `connection` string with protocol and optional address,
credentials and/or path. Read details below for more information about supported
protocols.

Once environment configuration file is ready you can start using Creep. Just
type `creep <name>` where `<name>` is name of a configured location. When no
name is specified location `default` is used.

Creep will then connect to remote location and try to retrieve information from
last deployment to compute incremental tasks. When you deploy for the first time
this information won't be available and Creep will ask you if a full deploy
should be performed instead. After each successful deployment it will save
information on remote location in a `.creep.rev` file.

While storing deployment information on remote location keeps related data
altogether and works even if you're not the only one performing deployments,
you may prefer to store them locally instead. In that case just add a new
`local` option with value `true` for all affected locations in your
`.creep.env` file:

	{
		...
		"integration": {
			"connection": "ftp://me:password@my-dev-server/www-data/",
			"local": true
		},
		...
	}

You can specify additional options depending on the protocol you're using. To
specify options just add an `options` property containing required options as a
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

Note that environment files only describe information about external locations
and may contain passwords. For those reasons they should be excluded from your
versionning.

Definition file
---------------

Creep supports another configuration file, called _definition_ file and used to
define how local changes must be detected and what pre-processing operations
must be applied to files before transferring them. This file must be named
`.creep.def` and be located in the same folder(s) than your environment
configuration file(s). As opposed to the environment file, definition file is
bound to your project and shouldn't be excluded from versionning.

Definition configuration file uses JSON format and looks like this:

	{
		"source": "hash",
		"options": {
			"algorithm": "md5",
			"follow": false
		},
		"modifiers": [
			{
				"pattern": "\\.dist$",
				"filter": "false"
			}
		]
	}

The `source` part specifies how Creep should analyze differences when you
execute it inside this directory. When this option is not specified Creep will
auto-detect it based on current environment. The `options` allows you to tune
behavior of the selected `source` by specifying custom parameters. Here is the
list of supported sources and associated options:

- Git versionning:
  - Specify `git` source so local `git` executable is used to get diff between
    two revisions. When using this mode Creep relies on Git history and only
    needs to remember which revision has been deployed. It also allows you to
    manually specify the revision you want to deploy through command line
    argument.
  - No options are available for this source type.
- File hash:
  - Specify `hash` source to have Creep computing a hash of each file to detect
    differences. This mode has a higher overhead than Git since it has to save
    a value for each file rather than one unique revision, but can work with any
    regular folder.
  - String option `algorithm` selects the hashing algorithm to be used among
    sha1, sha256, sha512 or md5 (default).
  - Boolean option `follow` specifies whether symbolic links should be
    followed or ignored (default).

The `modifiers` part allow you to define pre-processing operations that should
be triggered on files before they're sent to remote locations (e.g. rename,
compile, minify, obfuscate, etc.). Each modifier must define a regular
expression in its `pattern` property used to select files it should affect, plus
a set of processing actions that will be applied on matched files.

Here is an example of `modifiers` section in a definition configuration
(remember backslashes must be escaped in JSON, hence the double `\\` used in
regular expression patterns):

	{
		...
		"modifiers": [
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
		...
	}

Modifiers are evaluated in sequence and each file can only match one single
modifier: evaluation stops after the first matched pattern. For each file
matching a modifier, associated actions (if any) are applied on it. Available
modifier actions are listed below:

- `filter` action specifies a shell command to be executed, where special `{}`
  token is replaced by an absolute path to the file being matched. If this
  command returns a non-zero result file won't be sent to remote location.
  - In the example above, the `false` command is used to exclude files with name
    ending with `.dist` from deployment.
  - Empty string value can also be used to always exclude files. It's equivalent
    to the `false` command used in the example above but has better portability.
- `rename` action specifies a new name for file and supports back references on
  the regular expression used in `pattern`.
  - In the example above, files ending with `.less` will have their extension
    changed to `.css`: the back reference `\\1` captured original file name
    without extension in associated pattern.
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

A default modifier is always added as last element of the list to filter the
environment file out of deployments, since it shouldn't be transferred. You may
override this behavior by adding an explicit modifier on this file.

Troubleshooting
---------------

This project is still under develpement and may not behave as you would expect.
The `-v` (verbose) switch may help you understanding how your environment and
modifiers files are used in case of issue.

If you really can't figure out what's happening, don't hesitate to create an
issue on GitHub or contact me directly!
