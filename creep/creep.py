#!/usr/bin/env python3

import argparse
import logging
import os
import sys

sys.path.append(os.path.dirname(__file__))

from src import Application, Logger, load


def main():
    parser = argparse.ArgumentParser(prog='Creep',
                                     description='Perform incremental deployment from workspace to remote directory.')

    parser.add_argument('names',
                        nargs='*',
                        help='Target location name (e.g. "production" ; use "*" to deploy to all locations)')

    parser.add_argument('-a',
                        '--append',
                        action='append',
                        default=[],
                        help='Manually append file or directory to locations',
                        metavar='PATH')

    parser.add_argument('-b',
                        '--base-dir',
                        default='.',
                        help='Base directory used to resolve relative paths in definition file',
                        metavar='DIR')

    parser.add_argument('-d',
                        '--definition',
                        default='.',
                        help='Read definition configuration from specified file, directory or JSON string',
                        metavar='FILE/JSON')

    parser.add_argument('-f',
                        '--rev-from',
                        help='Use given initial version instead of reading it from revision file',
                        metavar='REV')

    parser.add_argument('--no-color',
                        action='store_true',
                        default=False,
                        help='Disable ANSI color codes in output logs')

    parser.add_argument('-q',
                        '--quiet',
                        dest='level',
                        action='store_const',
                        const=logging.WARNING,
                        default=logging.INFO,
                        help='Quiet mode, don\'t display anything but errors')

    parser.add_argument('-r',
                        '--remove',
                        action='append',
                        default=[],
                        help='Manually remove file or directory from locations',
                        metavar='PATH')

    parser.add_argument('-t',
                        '--rev-to',
                        help='Use given target version instead of reading it from current workspace',
                        metavar='REV')

    parser.add_argument('-v',
                        '--verbose',
                        dest='level',
                        action='store_const',
                        const=logging.DEBUG,
                        default=logging.INFO,
                        help='Verbose mode, display extra information')

    parser.add_argument('-y',
                        '--yes',
                        action='store_true',
                        default=not sys.stdout.isatty(),
                        help='Skip every prompt and always assume "yes" answer instead')

    parser.add_argument('--extra-append', action='append', default=[], help=argparse.SUPPRESS)
    parser.add_argument('--extra-remove', action='append', default=[], help=argparse.SUPPRESS)

    args = parser.parse_args()
    logger = Logger.build(args.level, args.no_color)

    application = Application(logger, args.yes)

    if args.definition[0:1] == '{' and args.definition[-1:] == '}':
        definition_config = json.loads(args.definition)
    else:
        definition_config = args.definition

    definition = load(logger, args.base_dir, definition_config)

    if definition is None:
        return 1

    append = args.append + args.extra_append
    remove = args.remove + args.extra_remove

    if not application.run(definition, args.names, append, remove, args.rev_from, args.rev_to):
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
