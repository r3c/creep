#!/usr/bin/env python

import subprocess

class Process:
	def __init__ (self, args):
		self.args = args
		self.directory = None
		self.shell = False
		self.stdin = None

	def execute (self):
		process = subprocess.Popen (self.args, cwd = self.directory, shell = self.shell, stdin = self.stdin and subprocess.PIPE or None, stdout = subprocess.PIPE)
		output = process.communicate (input = self.stdin)

		if process.returncode != 0:
			return None

		return output[0]

	def set_directory (self, directory):
		self.directory = directory

		return self

	def set_shell (self, shell):
		self.shell = shell

		return self

	def set_stdin (self, stdin):
		self.stdin = stdin

		return self
