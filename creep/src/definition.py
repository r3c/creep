#!/usr/bin/env python3

import os
import re
import shlex
import shutil
import urllib.parse

from .action import Action
from .configuration import Configuration
from .process import Process


def _join_path(a, b):
    return os.path.normpath(os.path.join(a, b))


class DefinitionModifier:

    def __init__(self, regex, rename, link, modify, chmod, filter):
        self.chmod = chmod
        self.filter = filter
        self.link = link
        self.modify = modify
        self.regex = regex
        self.rename = rename


class Definition:

    def __init__(
        self, logger, origin, environment, tracker, options, cascades, modifiers, path
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


def _load_definition(logger, parent):
    ignores = []
    configuration = parent.get_include(".creep.def", ignores)

    if configuration is None:
        return None

    # Read cascades from JSON configuration
    cascades_list = configuration.read_field("cascades").read_list()
    cascades = [_load_definition(logger, cascade) for cascade in cascades_list]

    if None in cascades:
        return None

    # Read modifiers from JSON configuration
    modifiers_list = configuration.read_field("modifiers").read_list()
    modifiers = [_load_modifier(modifier) for modifier in modifiers_list]

    if None in modifiers:
        return None

    # Read scalar properties from JSON configuration
    environment = _load_environment(configuration.read_field("environment"), ignores)
    origin = _load_origin(configuration.read_field("origin"))
    tracker = configuration.read_field("tracker", ["source"]).read_value(str, None)

    if environment is None or origin is None:
        return None

    # Read options
    options_object = configuration.read_field("options").read_object()
    options = dict((key, c.read_value(str, None)) for key, c in options_object.items())

    if None in options.values():
        return None

    for key in configuration.get_orphan_keys():
        configuration.log_warning('Ignored unknown property "{key}"', key=key)

    path = configuration.path

    definition = Definition(
        logger, origin, environment, tracker, options, cascades, modifiers, path
    )

    for ignore in set((os.path.basename(ignore) for ignore in ignores)):
        definition.ignore(ignore)

    return definition


def _load_environment(parent, ignores):
    configuration = parent.get_include(".creep.env", ignores)

    if configuration is None:
        return None

    environment_object = configuration.read_object()
    locations = {
        name: _load_location(location) for name, location in environment_object.items()
    }

    if None in locations.values():
        return None

    return Environment(locations, configuration.path)


def _load_location(configuration: Configuration):
    append_files_list = configuration.read_field("append_files").read_list()
    append_files = [c.read_value(str, None) for c in append_files_list]
    connection = configuration.read_field("connection").read_value(str, None)
    local = configuration.read_field("local").read_value(bool, False)
    options_object = configuration.read_field("options").read_object()
    options = dict((key, c.read_value(str, None)) for key, c in options_object.items())
    remove_files_list = configuration.read_field("remove_files").read_list()
    remove_files = [c.read_value(str, None) for c in remove_files_list]
    state = configuration.read_field("state").read_value(str, ".creep.rev")

    if None in append_files or None in remove_files:
        return None

    for key in configuration.get_orphan_keys():
        configuration.log_warning('Ignored unknown property "{key}"', key=key)

    return EnvironmentLocation(
        append_files, connection, local, options, remove_files, state
    )


def _load_modifier(configuration):
    chmod = configuration.read_field("chmod").read_value(str, None)
    filter = configuration.read_field("filter").read_value(str, None)
    link = configuration.read_field("link").read_value(str, None)
    modify = configuration.read_field("modify", ["adapt"]).read_value(str, None)
    pattern = configuration.read_field("pattern").read_value(str, None)
    rename = configuration.read_field("rename", ["name"]).read_value(str, None)

    if pattern is None:
        configuration.log_warning("Undefined modifier pattern")

        return None

    chmod_integer = chmod is not None and int(chmod, 8) or None
    pattern_regex = re.compile(pattern)

    for key in configuration.get_orphan_keys():
        configuration.log_warning('Ignored unknown property "{key}"', key=key)

    return DefinitionModifier(
        pattern_regex, rename, link, modify, chmod_integer, filter
    )


def _load_origin(configuration):
    origin = configuration.read_value(str, ".")
    origin_url = urllib.parse.urlparse(origin)

    if origin_url.scheme == "" or origin_url.scheme == "file":
        # Hack: force triple slash before path so urllib preserves them. This will produce a URL with pattern
        # "file:///something" where "something" can be an absolute (starting with /) or relative path. After parsing
        # the URL, removing leading slash from path will give us back the original value of "something".
        original = _join_path(os.path.dirname(configuration.path), origin_url.path)

        return origin_url._replace(scheme="file", path="/" + original).geturl()

    return origin


def load(logger, base_directory, object_or_path):
    # Hack: force add . after configuration path
    path = os.path.join(base_directory, ".")
    configuration = Configuration(logger, path, "", object_or_path, False)

    return _load_definition(logger, configuration)
