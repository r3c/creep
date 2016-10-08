#!/usr/bin/env python

import logging
import os
import shutil
import sys
import tempfile
import unittest

sys.path.append (os.path.dirname (os.path.dirname (__file__)))

from src import Deployer, Logger

class DeployerTester (unittest.TestCase):
	def execute (self, steps):
		directory = tempfile.mkdtemp ()

		try:
			source = os.path.join (directory, 'source')
			target = os.path.join (directory, 'target')

			os.makedirs (source)
			os.makedirs (target)

			for step in steps:
				step (source, target)
		finally:
			shutil.rmtree (directory)

	def step_create_environment (self, source, environment):
		with open (os.path.join (source, '.creep.env'), 'wb') as file:
			file.write (environment)

	def step_deploy (self, source, locations, files, definition = '.creep.def', environment = '.creep.env'):
		for relative, data in files.items ():
			directory = os.path.join (source, os.path.dirname (relative))

			if not os.path.exists (directory):
				os.makedirs (directory)

			with open (os.path.join (source, relative), 'wb') as file:
				file.write (data)

		deployer = Deployer (Logger.build (logging.CRITICAL), definition, environment, True)

		self.assertTrue (deployer.deploy (source, locations, [], [], None, None))

	def step_expect (self, target, files):
		for relative, expected in files.items ():
			path = os.path.join (target, relative)

			self.assertEqual (os.path.exists (path), expected is not None)

			if expected is not None:
				with open (path, 'rb') as file:
					data = file.read ()

				self.assertEqual (data, expected)

	def test_config_inline_definition (self):
		self.execute ([
			lambda s, t: self.step_create_environment (s, b'{"default": {"connection": "file:///../target"}}'),
			lambda s, t: self.step_deploy (s, ['default'], {'aaa': b'a', 'bbb': b'b'}, '{"modifiers": [{"pattern": "^bbb$", "filter": ""}]}'),
			lambda s, t: self.step_expect (t, {'aaa': b'a', 'bbb': None})
		])

	def test_config_inline_environment (self):
		files = {'aaa': b'a'}

		self.execute ([
			lambda s, t: self.step_deploy (s, ['default'], files, '.creep.def', '{"default": {"connection": "file:///../target"}}'),
			lambda s, t: self.step_expect (t, files)
		])

	def test_file_basic_many (self):
		files = {'aaa': b'a', 'b/bb': b'b', 'c/c/c': b'c'}

		self.execute ([
			lambda s, t: self.step_create_environment (s, b'{"default": {"connection": "file:///../target"}}'),
			lambda s, t: self.step_deploy (s, ['default'], files),
			lambda s, t: self.step_expect (t, files)
		])

	def test_file_basic_one (self):
		files = {'test': b'Hello, World!'}

		self.execute ([
			lambda s, t: self.step_create_environment (s, b'{"default": {"connection": "file:///../target"}}'),
			lambda s, t: self.step_deploy (s, ['default'], files),
			lambda s, t: self.step_expect (t, files)
		])

if __name__ == '__main__':
    unittest.main ()
