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


def __load_definition(logger, parent):
    ignores = []
    configuration = parent.get_include(".creep.def", ignores)

    if configuration is None:
        return None

    # Read cascades from JSON configuration
    cascades_array = configuration.read_field("cascades").get_array()

    if cascades_array is None:
        return None

    cascades = [__load_definition(logger, cascade) for cascade in cascades_array]

    if None in cascades:
        return None

    # Read modifiers from JSON configuration
    modifiers_array = configuration.read_field("modifiers").get_array()

    if modifiers_array is None:
        return None

    modifiers = [__load_modifier(modifier) for modifier in modifiers_array]

    if None in modifiers:
        return None

    # Read scalar properties from JSON configuration
    environment = __load_environment(configuration.read_field("environment"), ignores)
    options = configuration.read_field("options").get_value(dict, {})
    origin = __load_origin(configuration.read_field("origin"))
    tracker = configuration.read_field("tracker", ["source"]).get_value(str, None)

    if environment is None or not options[1] or origin is None or not tracker[1]:
        return None

    for key in configuration.get_orphan_keys():
        configuration.log_warning('Ignored unknown property "{key}"', key=key)

    path = configuration.path

    definition = Definition(
        logger, origin, environment, tracker[0], options[0], cascades, modifiers, path
    )

    for ignore in set((os.path.basename(ignore) for ignore in ignores)):
        definition.ignore(ignore)

    return definition


def __load_environment(parent, ignores):
    configuration = parent.get_include(".creep.env", ignores)

    if configuration is None:
        return None

    environment_object = configuration.get_object()

    if environment_object is None:
        return None

    locations = {
        name: __load_location(location) for name, location in environment_object.items()
    }

    if None in locations.values():
        return None

    return Environment(locations, configuration.path)


def __load_location(configuration):
    append_files = configuration.read_field("append_files").get_value(list, [])
    connection = configuration.read_field("connection").get_value(str, None)
    local = configuration.read_field("local").get_value(bool, False)
    options = configuration.read_field("options").get_value(dict, {})
    remove_files = configuration.read_field("remove_files").get_value(list, [])
    state = configuration.read_field("state").get_value(str, ".creep.rev")

    if (
        not append_files[1]
        or not connection[1]
        or not local[1]
        or not options[1]
        or not remove_files[1]
        or not state[1]
    ):
        return None

    for key in configuration.get_orphan_keys():
        configuration.log_warning('Ignored unknown property "{key}"', key=key)

    return EnvironmentLocation(
        append_files[0], connection[0], local[0], options[0], remove_files[0], state[0]
    )


def __load_modifier(configuration):
    chmod = configuration.read_field("chmod").get_value(str, None)
    filter = configuration.read_field("filter").get_value(str, None)
    link = configuration.read_field("link").get_value(str, None)
    modify = configuration.read_field("modify", ["adapt"]).get_value(str, None)
    pattern = configuration.read_field("pattern").get_value(str, None)
    rename = configuration.read_field("rename", ["name"]).get_value(str, None)

    if (
        not chmod[1]
        or not filter[1]
        or not link[1]
        or not modify[1]
        or not pattern[1]
        or not rename[1]
    ):
        return None

    if pattern[0] is None:
        configuration.log_error("Undefined modifier pattern")

        return None

    chmod_integer = chmod[0] is not None and int(chmod[0], 8) or None
    pattern_regex = re.compile(pattern[0])

    for key in configuration.get_orphan_keys():
        configuration.log_warning('Ignored unknown property "{key}"', key=key)

    return DefinitionModifier(
        pattern_regex, rename[0], link[0], modify[0], chmod_integer, filter[0]
    )


def __load_origin(configuration):
    origin = configuration.get_value(str, ".")

    if not origin[1]:
        return None

    origin_value = origin[0]
    origin_url = urllib.parse.urlparse(origin_value)

    if origin_url.scheme == "" or origin_url.scheme == "file":
        # Hack: force triple slash before path so urllib preserves them. This will produce a URL with pattern
        # "file:///something" where "something" can be an absolute (starting with /) or relative path. After parsing
        # the URL, removing leading slash from path will give us back the original value of "something".
        original = _join_path(os.path.dirname(configuration.path), origin_url.path)

        return origin_url._replace(scheme="file", path="/" + original).geturl()

    return origin_value


def load(logger, base_directory, object_or_path):
    # Hack: force add . after configuration path
    configuration = Configuration(
        logger, os.path.join(base_directory, "."), "", object_or_path, False
    )

    return __load_definition(logger, configuration)
