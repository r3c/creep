#!/usr/bin/python3

import argparse
import logging
import os
import sys

sys.path.append(os.path.dirname(__file__))

from src import Deployer, Logger


def main():
    parser = argparse.ArgumentParser(prog='Creep',
                                     description='Perform incremental deployment from workspace to remote directory.')

    parser.add_argument('name', nargs='*', help='Deploy to specified named location (* = everywhere)')

    parser.add_argument('-a',
                        '--append',
                        action='append',
                        default=[],
                        help='Manually append file or directory to locations',
                        metavar='PATH')

    parser.add_argument('-b',
                        '--base',
                        default='.',
                        help='Use given path to workspace instead of current directory',
                        metavar='DIR')

    parser.add_argument('-d',
                        '--definition',
                        default='.creep.def',
                        help='Read definition configuration from specified file or JSON string',
                        metavar='FILE/JSON')

    parser.add_argument('-e',
                        '--environment',
                        default='.creep.env',
                        help='Read environment configuration from specified file or JSON string',
                        metavar='FILE/JSON')

    parser.add_argument('-f',
                        '--rev-from',
                        help='Use given initial version instead of reading it from revision file',
                        metavar='REV')

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
                        help='Skip every prompt and always assume "yes" answer instead')

    parser.add_argument('--extra-append', action='append', default=[], help=argparse.SUPPRESS)
    parser.add_argument('--extra-remove', action='append', default=[], help=argparse.SUPPRESS)

    args = parser.parse_args()
    logger = Logger.build(args.level)

    deployer = Deployer(logger, args.definition, args.environment, args.yes)

    append = args.append + args.extra_append
    remove = args.remove + args.extra_remove

    return not deployer.deploy(args.base, args.name, append, remove, args.rev_from, args.rev_to) and 1 or 0


if __name__ == '__main__':
    sys.exit(main())
