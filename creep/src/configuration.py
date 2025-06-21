#!/usr/bin/env python3

import json
import os

from typing import Dict, List, Self


class Configuration:

    def __init__(self, logger, path, position, value, undefined):
        self.logger = logger
        self.path = path
        self.position = position
        self.undefined = undefined
        self.value = value

    def __repr__(self):
        return str(self.value)

    def get_include(self, default_filename, ignores):
        if isinstance(self.value, dict):
            return Configuration(
                self.logger, self.path, self.position, self.value, False
            )

        include = self.undefined and "." or self.value

        if isinstance(include, str):
            include_combined = os.path.join(os.path.dirname(self.path), include)

            if os.path.isdir(include_combined):
                include_path = os.path.join(include_combined, default_filename)
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

    def get_undefined(self, position):
        return Configuration(self.logger, self.path, position, None, True)

    def get_orphan_keys(self) -> List[str]:
        if isinstance(self.value, dict):
            return self.value.keys()

        return []

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

    def read_field(self, primary: str, alternatives: List[str] = []) -> Self:
        position = self.position

        if isinstance(self.value, dict):
            deprecated = False

            for key in [primary] + alternatives:
                position = "{parent}.{key}".format(key=key, parent=self.position)
                value = self.value.get(key, None)

                if value is not None:
                    self.value.pop(key)

                    if deprecated:
                        self.log_warning(
                            'Deprecated property "{key}" should be replaced by "{primary}"',
                            key=key,
                            primary=primary,
                        )

                    return Configuration(self.logger, self.path, position, value, False)

                deprecated = True

        elif not self.undefined:
            self.log_warning("Property must be an object with keys and values")

        return self.get_undefined(position)

    def read_object(self) -> Dict[str, Self]:
        result = {}

        if isinstance(self.value, dict):
            for key, value in self.value.items():
                position = "{parent}.{key}".format(key=key, parent=self.position)
                item = Configuration(self.logger, self.path, position, value, False)

                result[key] = item

            self.value.clear()

        elif not self.undefined:
            self.log_warning("Property must be an object with keys and values")

        return result

    def read_list(self) -> List[Self]:
        result = []

        if isinstance(self.value, list):
            for index, value in enumerate(self.value):
                position = "{parent}[{index}]".format(index=index, parent=self.position)
                item = Configuration(self.logger, self.path, position, value, False)

                result.append(item)

        elif not self.undefined:
            self.log_warning("Property must be an array of elements")

        return result

    def read_value(self, type, default):
        if isinstance(self.value, type):
            return self.value

        elif not self.undefined:
            self.log_warning('Property must have type "{type}"', type=type)

        return default
