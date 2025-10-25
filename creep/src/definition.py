#!/usr/bin/env python3

import logging
import os
import re
import shlex
import shutil
import urllib.parse

from logging import Logger
from typing import List
from urllib.parse import SplitResult

from .action import Action
from .configuration import Configuration
from .process import Process


definition_default_name = ".creep.def"
environment_default_name = ".creep.env"


def _join_path(a: str, b: str) -> str:
    return os.path.normpath(os.path.join(a, b))


class DefinitionModifier:

    def __init__(
        self,
        regex: re.Pattern,
        rename,
        link,
        modify,
        chmod: int | None,
        filter: str | None,
    ):
        self.chmod = chmod
        self.filter = filter
        self.link = link
        self.modify = modify
        self.regex = regex
        self.rename = rename


class Definition:

    def __init__(
        self,
        logger: Logger,
        origin: SplitResult,
        environment: Environment,
        tracker,
        options,
        cascades,
        modifiers,
        path,
    ):
        self.cascades = cascades
        self.environment = environment
        self.logger = logger
        self.modifiers = modifiers
        self.options = options
        self.origin = origin
        self.path = path
        self.tracker = tracker

    def apply(self, base_directory, path, type, used):
        # Ensure we don't process a file already scanned
        path = os.path.normpath(path)

        if path in used:
            return []

        used.add(path)

        # Find modifier matching current file name if any
        name = os.path.basename(path)

        for modifier in self.modifiers:
            match = modifier.regex.search(name)

            if match is None:
                continue

            self.logger.debug(
                "File '{0}' matches '{1}'.".format(path, modifier.regex.pattern)
            )

            actions = []

            # Apply renaming pattern if any
            if modifier.rename is not None:
                previous_path = path

                name = os.path.basename(
                    re.sub(
                        "\\\\([0-9]+)",
                        lambda m: match.group(int(m.group(1))),
                        modifier.rename,
                    )
                )
                path = _join_path(os.path.dirname(path), name)

                if type == Action.ADD:
                    # FIXME: must duplicate instead of rename so that references (e.g. links) won't break ; should be renamed at upload only instead
                    shutil.copyfile(
                        _join_path(base_directory, previous_path),
                        _join_path(base_directory, path),
                    )

                self.logger.debug(
                    "File '{0}' was renamed to '{1}'.".format(previous_path, path)
                )

            # Apply link command if any
            if modifier.link is not None and type == Action.ADD:
                self.logger.debug(
                    "Applying 'link' command '{1}' on file '{0}'.".format(
                        path, modifier.modify
                    )
                )

                out = self.run(base_directory, path, modifier.link)

                if out is not None:
                    for link in out.decode("utf-8").splitlines():
                        self.logger.debug(
                            "File '{0}' was linked to file '{1}'.".format(path, link)
                        )

                        actions.extend(self.apply(base_directory, link, type, used))
                else:
                    self.logger.warning(
                        "Command 'link' on file '{path}' returned non-zero code.".format(
                            path=path
                        )
                    )

                    type = Action.ERR

            # Build output file using processing command if any
            if modifier.modify is not None and type == Action.ADD:
                self.logger.debug(
                    "Applying 'modify' command '{1}' on file '{0}'.".format(
                        path, modifier.modify
                    )
                )

                out = self.run(base_directory, path, modifier.modify)

                if out is not None:
                    with open(_join_path(base_directory, path), "wb") as file:
                        file.write(out)
                else:
                    self.logger.warning(
                        "Command 'modify' on file '{path}' returned non-zero code.".format(
                            path=path
                        )
                    )

                    type = Action.ERR

            # Set file mode
            if modifier.chmod is not None and type == Action.ADD:
                os.chmod(_join_path(base_directory, path), modifier.chmod)

            # Apply filtering command if any
            if modifier.filter is not None:
                self.logger.debug(
                    "Applying 'filter' command '{1}' on file '{0}'.".format(
                        path, modifier.filter
                    )
                )

                if (
                    modifier.filter == ""
                    or self.run(base_directory, path, modifier.filter) is None
                ):
                    self.logger.debug("File '{0}' was filtered out.".format(path))

                    type = Action.NOP

            # Append action to list and return
            actions.append(Action(path, type))

            return actions

        # No modifier matched, return unmodified input
        return [Action(path, type)]

    def ignore(self, filename):
        regex = re.compile("^" + re.escape(filename) + "$")

        self.modifiers.append(DefinitionModifier(regex, None, None, None, 0o644, ""))

    def run(self, base_directory, path, command):
        arguments = command.replace("{}", shlex.quote(path))
        result = (
            Process(arguments).set_directory(base_directory).set_shell(True).execute()
        )

        if not result:
            self.logger.debug(result.err.decode("utf-8"))

            return None

        return result.out


class EnvironmentLocation:

    def __init__(self, append_files, connection, local, options, remove_files, state):
        self.append_files = append_files
        self.connection = connection
        self.local = local
        self.options = options
        self.remove_files = remove_files
        self.state = state


class Environment:

    def __init__(self, locations, path):
        self.locations = locations
        self.path = path


def _load_definition(
    logger: logging.Logger, configuration: Configuration, includes: List[str]
) -> Definition | None:
    # Read cascades from JSON configuration
    cascades = []

    for item in configuration.open_field("cascades").open_list():
        item.set_default_name(definition_default_name)
        cascade = _load_definition(logger, item, includes)

        if cascade is None:
            return None

        cascades.append(cascade)

    # Read modifiers from JSON configuration
    modifiers = []

    for item in configuration.open_field("modifiers").open_list():
        modifier = _load_modifier(item)

        if modifier is None:
            return None

        modifiers.append(modifier)

    # Read scalar properties from JSON configuration
    environment_field = configuration.open_field("environment", [], ".")
    environment_field.set_default_name(environment_default_name)
    environment = _load_environment(environment_field)
    origin = _load_origin(configuration.open_field("origin"))
    tracker = configuration.open_field("tracker", ["source"]).read_value(str, None)

    if environment is None or origin is None:
        return None

    # Read options
    options = {}

    for key, value in configuration.open_field("options").open_object().items():
        option = value.read_value(str, None)

        if option is None:
            return None

        options[key] = option

    for key in configuration.get_orphan_keys():
        configuration.log_warning('Ignored unknown property "{key}"', key=key)

    # Sanity check
    if configuration.invalid:
        return None

    # Build definition and return
    definition = Definition(
        logger,
        origin,
        environment,
        tracker,
        options,
        cascades,
        modifiers,
        configuration.path,
    )

    # FIXME: this is adding every included base name from every definition into current one, it should be isolated
    # instead by definition instead.
    ignores = set(os.path.basename(include) for include in includes)

    for ignore in ignores:
        definition.ignore(ignore)

    return definition


def _load_environment(configuration: Configuration) -> Environment | None:
    locations = {}

    for key, value in configuration.open_object().items():
        location = _load_location(value)

        if location is None:
            return None

        locations[key] = location

    if configuration.invalid:
        return None

    return Environment(locations, configuration.path)


def _load_location(configuration: Configuration) -> EnvironmentLocation | None:
    append_files_list = configuration.open_field("append_files").open_list()
    append_files = [c.read_value(str, None) for c in append_files_list]
    connection = configuration.open_field("connection").read_value(str, None)
    local = configuration.open_field("local").read_value(bool, False)
    options_object = configuration.open_field("options").open_object()
    options = dict((key, c.read_value(str, None)) for key, c in options_object.items())
    remove_files_list = configuration.open_field("remove_files").open_list()
    remove_files = [c.read_value(str, None) for c in remove_files_list]
    state = configuration.open_field("state").read_value(str, ".creep.rev")

    if None in append_files or None in remove_files:
        return None

    for key in configuration.get_orphan_keys():
        configuration.log_warning('Ignored unknown property "{key}"', key=key)

    if configuration.invalid:
        return None

    return EnvironmentLocation(
        append_files, connection, local, options, remove_files, state
    )


def _load_modifier(configuration: Configuration) -> DefinitionModifier | None:
    chmod = configuration.open_field("chmod").read_value(str, None)
    filter = configuration.open_field("filter").read_value(str, None)
    link = configuration.open_field("link").read_value(str, None)
    modify = configuration.open_field("modify", ["adapt"]).read_value(str, None)
    pattern = configuration.open_field("pattern").read_value(str, None)
    rename = configuration.open_field("rename", ["name"]).read_value(str, None)

    if pattern is None:
        configuration.log_warning("Undefined modifier pattern")

        return None

    chmod_integer = chmod is not None and int(chmod, 8) or None
    pattern_regex = re.compile(pattern)

    for key in configuration.get_orphan_keys():
        configuration.log_warning('Ignored unknown property "{key}"', key=key)

    if configuration.invalid:
        return None

    return DefinitionModifier(
        pattern_regex, rename, link, modify, chmod_integer, filter
    )


def _load_origin(configuration: Configuration) -> SplitResult | None:
    origin = urllib.parse.urlsplit(str(configuration.read_value(str, ".")))

    if origin.scheme == "" or origin.scheme == "file":
        relative_path = _join_path(os.path.dirname(configuration.path), origin.path)
        origin = origin._replace(path=relative_path)

    return origin


def load(logger, base_directory, object_or_path):
    includes = []
    path = os.path.join(base_directory, "dummy")

    configuration = Configuration(logger, includes, path, ".", object_or_path)
    configuration.set_default_name(definition_default_name)

    return _load_definition(logger, configuration, includes)
