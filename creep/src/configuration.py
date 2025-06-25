#!/usr/bin/env python3

import json
import logging
import os

from typing import Dict, List, Self


class Configuration:

    def __init__(
        self,
        logger: logging.Logger,
        includes: List[str],
        path: str,
        position: str,
        value: any,
    ):
        self.default_name = None
        self.includes = includes
        self.invalid = False
        self.logger = logger
        self.path = path
        self.position = position
        self.value = value

    def __repr__(self):
        return str(self.value)

    def get_orphan_keys(self) -> List[str]:
        if isinstance(self.value, dict):
            return self.value.keys()

        return []

    def log_warning(self, prefix, **kwargs):
        message = prefix + " in {path}:{position}"

        self.logger.warning(
            message.format(
                message=message, path=self.path, position=self.position, **kwargs
            )
        )

    def open_field(
        self,
        primary_key: str,
        alternative_keys: List[str] = [],
        fallback_value: any = None,
    ) -> Self:
        self.__try_include()

        if isinstance(self.value, dict):
            deprecated = False

            for key in [primary_key] + alternative_keys:
                value = self.value.get(key, None)

                if value is not None:
                    self.value.pop(key)

                    if deprecated:
                        self.log_warning(
                            'Deprecated property "{key}" should be replaced by "{primary_key}"',
                            deprecated_key=key,
                            primary_key=primary_key,
                        )

                    return self.__create_child(".{key}".format(key=key), value)

                deprecated = True

        elif self.value is not None:
            self.log_warning("Property must be an object with keys and values")

        return self.__create_child(".{key}".format(key=primary_key), fallback_value)

    def open_object(self) -> Dict[str, Self]:
        self.__try_include()

        result = {}

        if isinstance(self.value, dict):
            for key, value in self.value.items():
                item = self.__create_child(".{key}".format(key=key), value)

                result[key] = item

            self.value.clear()

        elif self.value is not None:
            self.log_warning("Property must be an object with keys and values")

        return result

    def open_list(self) -> List[Self]:
        self.__try_include()

        result = []

        if isinstance(self.value, list):
            for index, value in enumerate(self.value):
                item = self.__create_child("[{index}]".format(index=index), value)

                result.append(item)

        elif self.value is not None:
            self.log_warning("Property must be an array of elements")

        return result

    def read_value(self, type, default):
        if isinstance(self.value, type):
            return self.value

        elif self.value is not None:
            self.log_warning('Property must have type "{type}"', type=type)

        return default

    def set_default_name(self, name: str):
        self.default_name = name

    def __create_child(self, suffix: str, value: any):
        position = self.position + suffix

        return Configuration(self.logger, self.includes, self.path, position, value)

    def __log_debug(self, prefix, **kwargs):
        message = prefix + " in {path}:{position}"

        self.logger.debug(
            message.format(
                message=message, path=self.path, position=self.position, **kwargs
            )
        )

    def __try_include(self):
        if not isinstance(self.value, str):
            return

        self.path = os.path.join(os.path.dirname(self.path), self.value)

        if self.default_name is not None and os.path.isdir(self.path):
            self.path = os.path.join(self.path, self.default_name)

        if not os.path.isfile(self.path):
            self.__log_debug("File {include} does not exist".format(include=self.path))

            self.value = None

            return

        with open(self.path, "rb") as file:
            body = file.read().decode("utf-8")

        try:
            value = json.loads(body)
        except json.JSONDecodeError as error:
            self.log_warning(
                "File {include} is not a valid JSON ({error})",
                error=error,
                include=self.path,
            )

            self.invalid = True
            self.value = None

            return

        self.includes.append(self.path)
        self.value = value
