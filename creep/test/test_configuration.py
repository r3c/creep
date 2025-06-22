#!/usr/bin/env python3

import json
import logging
import os
import sys
import tempfile
import unittest

from unittest import mock

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.configuration import Configuration


class ConfigurationTester(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.directory.cleanup()

    def create_file(self, name: str, instance: object):
        path = os.path.join(self.directory.name, name)

        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "wb") as file:
            file.write(json.dumps(instance).encode("utf-8"))

        return path

    def load_configuration(self, name: str, logger: logging.Logger) -> Configuration:
        path = os.path.join(self.directory.name, name)

        with open(path, "rb") as file:
            root = json.load(file)

            return Configuration(logger, [], path, "", root)

    def load_object(self, instance: object, logger: logging.Logger) -> Configuration:
        self.create_file("configuration.json", instance)

        return self.load_configuration("configuration.json", logger)

    @mock.patch("logging.Logger")
    def test_get_orphan_keys(self, logger_mock):
        configuration = self.load_object({"f1": "a", "f2": "b", "f3": "c"}, logger_mock)
        configuration.read_field("f1")
        configuration.read_field("f3")

        self.assertListEqual(list(configuration.get_orphan_keys()), ["f2"])

        logger_mock.error.assert_not_called()
        logger_mock.warning.assert_not_called()

    @mock.patch("logging.Logger")
    def test_read_field_incompatible(self, logger_mock):
        configuration = self.load_object([], logger_mock)
        configuration.read_field("f1")

        logger_mock.error.assert_not_called()
        logger_mock.warning.assert_called_once()

        self.assertRegex(
            logger_mock.warning.call_args.args[0],
            "Property must be an object with keys and values in .*",
        )

    @mock.patch("logging.Logger")
    def test_read_field_valid(self, logger_mock):
        configuration = self.load_object({"f1": 42, "f2": "17"}, logger_mock)

        self.assertEqual(configuration.read_field("f1").read_value(int, None), 42)
        self.assertEqual(configuration.read_field("f2").read_value(str, None), "17")

        logger_mock.error.assert_not_called()
        logger_mock.warning.assert_not_called()

    @mock.patch("logging.Logger")
    def test_read_object_incompatible(self, logger_mock):
        configuration = self.load_object([], logger_mock)
        configuration.read_object()

        logger_mock.error.assert_not_called()
        logger_mock.warning.assert_called_once()

        self.assertRegex(
            logger_mock.warning.call_args.args[0],
            "Property must be an object with keys and values in .*",
        )

    @mock.patch("logging.Logger")
    def test_read_object_valid(self, logger_mock):
        configuration = self.load_object({"k1": 1, "k2": "2", "k3": False}, logger_mock)
        configuration_object = configuration.read_object()

        self.assertEqual(len(configuration_object), 3)
        self.assertEqual(configuration_object["k1"].read_value(int, None), 1)
        self.assertEqual(configuration_object["k2"].read_value(str, None), "2")
        self.assertEqual(configuration_object["k3"].read_value(bool, None), False)
        self.assertListEqual(list(configuration.get_orphan_keys()), [])

        logger_mock.error.assert_not_called()
        logger_mock.warning.assert_not_called()

    @mock.patch("logging.Logger")
    def test_read_list_incompatible(self, logger_mock):
        configuration = self.load_object({}, logger_mock)
        configuration.read_list()

        logger_mock.error.assert_not_called()
        logger_mock.warning.assert_called_once()

        self.assertRegex(
            logger_mock.warning.call_args.args[0],
            "Property must be an array of elements in .*",
        )

    @mock.patch("logging.Logger")
    def test_read_list_valid(self, logger_mock):
        configuration = self.load_object([1, "2", False], logger_mock)
        configuration_list = configuration.read_list()

        self.assertEqual(len(configuration_list), 3)
        self.assertEqual(configuration_list[0].read_value(int, None), 1)
        self.assertEqual(configuration_list[1].read_value(str, None), "2")
        self.assertEqual(configuration_list[2].read_value(bool, None), False)
        self.assertListEqual(list(configuration.get_orphan_keys()), [])

        logger_mock.error.assert_not_called()
        logger_mock.warning.assert_not_called()
