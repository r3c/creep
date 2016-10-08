#!/usr/bin/env python

import argparse
import logging
import os
import sys

sys.path.append (os.path.dirname (__file__))

from src import Deployer, Logger

def main ():
	# Parse command line options
	parser = argparse.ArgumentParser (description = 'Perform incremental deployment from Git/plain workspace to FTP/SSH/local folder.')
	parser.add_argument ('name', nargs = '*', help = 'Deploy to specified named location (* = everywhere)')
	parser.add_argument ('-a', '--append', action = 'append', default = [], help = 'Manually append file or directory to locations', metavar = 'PATH')
	parser.add_argument ('-b', '--base', default = '.', help = 'Change base directory', metavar = 'DIR')
	parser.add_argument ('--extra-append', action = 'append', default = [], help = argparse.SUPPRESS)
	parser.add_argument ('-e', '--environment', default = '.creep.env', help = 'Read environment configuration from specified file or JSON string', metavar = 'FILE/JSON')
	parser.add_argument ('-f', '--rev-from', help = 'Initial version used to compute diff', metavar = 'REV')
	parser.add_argument ('-d', '--definition', default = '.creep.def', help = 'Read definition configuration from specified file or JSON string', metavar = 'FILE/JSON')
	parser.add_argument ('-q', '--quiet', dest = 'level', action = 'store_const', const = logging.CRITICAL + 1, default = logging.INFO, help = 'Quiet mode, don\'t display anything but errors')
	parser.add_argument ('-r', '--remove', action = 'append', default = [], help = 'Manually remove file or directory from locations', metavar = 'PATH')
	parser.add_argument ('--extra-remove', action = 'append', default = [], help = argparse.SUPPRESS)
	parser.add_argument ('-t', '--rev-to', help = 'Target version used to compute diff', metavar = 'REV')
	parser.add_argument ('-v', '--verbose', dest = 'level', action = 'store_const', const = logging.DEBUG, default = logging.INFO, help = 'Verbose mode, display extra information')
	parser.add_argument ('-y', '--yes', action = 'store_true', help = 'Always answer yes to prompts')

	args = parser.parse_args ()
	deployer = Deployer (Logger.build (args.level), args.definition, args.environment, args.yes)

	if not deployer.deploy (
		args.base,
		args.name,
		args.append + args.extra_append,
		args.remove + args.extra_append,
		args.rev_from,
		args.rev_to):
		return 1

	return 0

if __name__ == '__main__':
	sys.exit (main ())
