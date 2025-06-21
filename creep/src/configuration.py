#!/usr/bin/env python3

import json
import os


def _join_path(a, b):
    return os.path.normpath(os.path.join(a, b))


class Configuration:

    def __init__(self, logger, path, position, value, undefined):
        self.logger = logger
        self.path = path
        self.position = position
        self.undefined = undefined
        self.value = value

    def __repr__(self):
        return str(self.value)

    def get_array(self):
        if self.undefined:
            return []

        if isinstance(self.value, list):
            position = lambda index: "{parent}[{index}]".format(
                index=index, parent=self.position
            )

            return [
                Configuration(self.logger, self.path, position(index), value, False)
                for index, value in enumerate(self.value)
            ]

        self.log_error("Property must be an array of elements")

        return None

    def get_include(self, default_filename, ignores):
        if isinstance(self.value, dict):
            return Configuration(
                self.logger, self.path, self.position, self.value, False
            )

        include = self.undefined and "." or self.value

        if isinstance(include, str):
            include_combined = _join_path(os.path.dirname(self.path), include)

            if os.path.isdir(include_combined):
                include_path = _join_path(include_combined, default_filename)
            else:
                include_path = include_combined

            if not os.path.isfile(include_path):
                return Configuration(self.logger, include_path, "", None, True)

            ignores.append(include_path)

            with open(include_path, "rb") as file:
                contents = file.read().decode("utf-8")

            try:
                root = json.loads(contents)
            except json.JSONDecodeError as error:
                self.log_error("Invalid JSON file: {error}", error=error)

                return None

            return Configuration(self.logger, include_path, "", root, False)

        self.log_error("Property must be an object or string")

        return None

    def get_object(self):
        if self.undefined:
            return {}

        if isinstance(self.value, dict):
            position = lambda key: "{parent}.{key}".format(
                key=key, parent=self.position
            )

            return {
                key: Configuration(self.logger, self.path, position(key), value, False)
                for key, value in self.value.items()
            }

        self.log_error("Property must be an object with keys and values")

        return None

    def get_undefined(self):
        return Configuration(self.logger, self.path, self.position, None, True)

    def get_value(self, type, default):
        if self.undefined:
            return (default, True)

        if isinstance(self.value, type):
            return (self.value, True)

        self.log_warning('Property must have type "{type}"', type=type)

        return (None, False)

    def log_error(self, prefix, **kwargs):
        message = prefix + " in {path}:{position}"

        self.logger.error(
            message.format(
                message=message, path=self.path, position=self.position, **kwargs
            )
        )

    def log_warning(self, prefix, **kwargs):
        message = prefix + " in {path}:{position}"

        self.logger.warning(
            message.format(
                message=message, path=self.path, position=self.position, **kwargs
            )
        )
