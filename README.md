Creep README file
=================

Overview
--------

Creep is an incremental deploy tool. It allows delta update from any Git
repository or a regular directory to a FTP or SSH remote server. Its purpose is
to deploy applications where files needed on remote servers (e.g. production)
match local files, that is to say when "deployment" actually means "copy with
some optional files preprocessing". For example it works best for HTML/CSS/JS
websites or server technologies like PHP.

Incremental deployment means Creep keeps track of deployed files on all remote
locations. Only modified files are transferred between two deployments. This
tracking mechanism depends on the type of directory used, for exemple Creep uses
revision hashes when deploying from a Git repository.

Installing
----------

You can install Creep using either pip or manual install from sources. If you
choose to use pip, just type the following:

	$ pip install creep
	$ creep -h # display help to ensure install worked properly

If you prefer manual install checkout the Git repository anywhere you want. Then
create a symbolic link in your `$PATH` to file `creep/creep.py`. Last step is
convenient but not mandatory, you can call Creep using full path to `creep.py`:

	$ git clone https://github.com/r3c/creep.git
	$ cd creep
	$ sudo ln -s creep/creep.py /usr/bin/creep
	$ creep -h # display help

After installation go to your project folder and continue reading to deploy your
first project.

Quick start
-----------

First go to the directory you want to deploy, e.g. the `src` folder of some
project. It can be inside a Git repository or just a regular folder, Creep will
select a suitable default configuration either way. Create a new `.creep.env`
file inside this directory with following JSON content:

	{
		"default": {
			"connection": "file:////tmp/creep-quickstart"
		}
	}

Mind the quadruple slash in `file:////tmp/creep-quickstart` string. Once file is
saved, create the directory and execute creep with no parameter:

	$ mkdir /tmp/creep-quickstart
	$ creep

Creep will tell you about deploying this project for the first time and ask you
to confirm. Enter `Y` to continue. It will display the full list of files in
your project (by scanning file system or Git history) then ask you again to
confirm. Enter `Y` and Creep will deploy your project to directory
`/tmp/creep-quickstart`.

Now if you try to execute creep again you'll see a message saying no action is
required. Deployment location now contains an up-to-date version of your project
and Creep saved this information. Try to change some file (and `git commit` them
if you were using Git) then execute the command again. This time Creep will send
only the file you changed rather than the full project.

This basic example shows how to incrementally deploy a project to some local
directory. Next sections will show how to deploy to remote locations (FTP or
SSH) and register several locations.

Environment file
----------------

As seen before Creep reads deployment location(s) from a configuration file
called _environment_ file. It contains one or more named location(s) pointing to
servers you want to deploy to. Name this file `.creep.env` and put it in any
directory you want to deploy.

Creep will deploy contents of this directory to remote location(s) and preserve
hierarchical structure. You can have several environment files in several
sub-directories inside your projet. For example one in `src` directory to deploy
executable code and another one in `assets` directory to deploy static files to
web servers.

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
must contain at least a `connection` string specifying protocol, address,
credentials and/or path. Read details below for more information about supported
protocols.

Once environment configuration file is ready you can start using Creep. Just
type `creep <name>` where `<name>` is name of a configured location. If you
don't specify any name Creep will deploy to `default` location.

Creep will then fetch last deployed revision from remote location and compute
difference. When you deploy for the first time there is no last deployed
revision so Creep will perform a full deploy. After each successful
deployment it will save revision to remote location in a `.creep.rev` file.

Storing revision information on remote location keeps related data altogether
and works well if you're not the only developer doing deployments. In case you
prefer storing them locally, just add a new `local` option with value `true`
for all affected locations in your `.creep.env` file:

	{
		...
		"integration": {
			"connection": "ftp://me:password@my-dev-server/www-data/",
			"local": true
		},
		...
	}

You can specify some options depending on the protocol you're using. To specify
options just add a `options` JSON object property holding required options:

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

Here is the list of supported protocols with expected connection string format
and available options:

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
  - Use connection format `ssh://user@host:port/path` with same variables than
    the ones used for FTP deployment. No password can be specified here so
    you'll need to either enter password manually or setup SSH keys and start
    SSH agent.
  - String option `extra` can be used to pass parameters to SSH command as shown
    in example above.

Path is relative by default in all protocols. Start your path by a slash `/`
character to specify an absolute path, e.g. `file:////var/opt/myproject`.

Note that environment files only describe information about external locations
and may contain passwords. For those reasons they should be excluded from your
versionning and kept only on machines performing deployments.

Definition file
---------------

Creep supports another configuration file, called _definition_ file. It's used
to define how to detect changes what preprocessing operations to apply on files
upon transfer. Name this file `.creep.def` and put it in the same directories
your environment files are. As opposed to environment files this one is bound to
your project and should be shared along with other project files.

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

The `modifiers` part defines actions to perform on files before they're sent to
remote locations (e.g. rename, compile, minify, obfuscate, etc.). Each modifier
must define a regular expression `pattern` property to select files it affects,
and processing actions that will be applied on them.

Here is an example of `modifiers` section in a definition configuration.
Remember backslashes must be escaped in JSON, hence the double `\\` used in
regular expression patterns:

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

Creep evaluates modifiers in sequence and one file can only match one modifier:
evaluation stops after the first matched one. For each file matching a modifier,
associated actions (if any) are applied on it. Available modifier actions are
listed below:

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

Creep always appends two modifiers to filter to exclude environment and
definition files from deployments. You shouldn't need to change this behavior,
but you may do so by adding explicit modifiers matching them.

Troubleshooting
---------------

This project is still under develpement and may not behave as you would expect.
In case of issue the `-v` (verbose) switch may help you understanding how your
environment and definition files are used.

If you can't figure out what's happening don't hesitate to open an issue on
GitHub or contact me!
