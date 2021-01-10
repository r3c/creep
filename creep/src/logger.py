#!/usr/bin/env python3

import logging
import re


class ColorStreamHandler(logging.StreamHandler):
    COLOR_BEGIN = '(('
    COLOR_BEGIN_RE = re.escape(COLOR_BEGIN)
    COLOR_END = '))'
    COLOR_END_RE = re.escape(COLOR_END)
    RESET = '\033[0m'

    def __init__(self, no_color, *args, **kwargs):
        super(ColorStreamHandler, self).__init__(*args, **kwargs)

        self.colors = {
            'black': '\033[0;30m',
            'maroon': '\033[0;31m',
            'green': '\033[0;32m',
            'olive': '\033[0;33m',
            'navy': '\033[0;34m',
            'purple': '\033[0;35m',
            'teal': '\033[0;36m',
            'silver': '\033[0;37m',
            'grey': '\033[1;30m',
            'red': '\033[1;31m',
            'lime': '\033[1;32m',
            'yellow': '\033[1;33m',
            'blue': '\033[1;34m',
            'fuchsia': '\033[1;35m',
            'cyan': '\033[1;36m',
            'white': '\033[1;37m',
            'reset': self.RESET
        }

        color_names = ['default'] + list(self.colors.keys())

        self.end = getattr(self, 'terminator', '\n')
        self.levels = {
            logging.CRITICAL: 'red',
            logging.DEBUG: 'olive',
            logging.ERROR: 'red',
            logging.INFO: 'white',
            logging.WARNING: 'yellow'
        }
        self.no_color = no_color
        self.tags = re.compile(self.COLOR_BEGIN_RE + '(' + '|'.join(color_names) + ')' + self.COLOR_END_RE)

    def is_tty(self):
        isatty = getattr(self.stream, 'isatty', None)

        return isatty and isatty()

    def emit(self, record):
        try:
            template = self.format(record)

            if not self.no_color and self.is_tty():
                prefix_name = self.levels.get(record.levelno, 'reset')
                prefix = self.COLOR_BEGIN + prefix_name + self.COLOR_END
                default = self.colors.get(prefix_name, self.RESET)

                message = self.tags.sub(lambda m: self.colors.get(m.group(1), default), prefix + template + self.RESET)
            else:
                message = self.tags.sub('', template)

            self.stream.write(message)
            self.stream.write(self.end)
            self.flush()

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class IndentLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, logger, extra):
        super(IndentLoggerAdapter, self).__init__(logger, extra)

        self.indent = 0

    def enter(self):
        self.indent += 1

    def leave(self):
        self.indent -= 1

    def process(self, msg, kwargs):
        return '| ' * max(min(self.indent, 8), 0) + msg, kwargs


class Logger:
    @staticmethod
    def build(level, no_color):
        formatter = logging.Formatter('%(levelname)s: %(message)s')

        console = ColorStreamHandler(no_color)
        console.setFormatter(formatter)

        logger = logging.getLogger()
        logger.addHandler(console)
        logger.setLevel(level)

        return IndentLoggerAdapter(logger, {})
