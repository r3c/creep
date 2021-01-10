#!/usr/bin/env python3

import subprocess


class ProcessResult:
    def __init__(self, code, out, err):
        self.code = code
        self.err = err
        self.out = out

    def __bool__(self):
        return self.code == 0

    def __nonzero__(self):
        return self.code == 0


class Process:
    def __init__(self, args):
        self.args = args
        self.directory = None
        self.input = None
        self.shell = False
        self.stdin = None

    def execute(self):
        process = subprocess.Popen(self.args,
                                   cwd=self.directory,
                                   shell=self.shell,
                                   stderr=subprocess.PIPE,
                                   stdin=self.stdin,
                                   stdout=subprocess.PIPE)

        (out, err) = process.communicate(self.input)

        return ProcessResult(process.returncode, out, err)

    def set_directory(self, directory):
        self.directory = directory

        return self

    def set_input(self, input):
        self.input = input
        self.stdin = subprocess.PIPE

        return self

    def set_shell(self, shell):
        self.shell = shell

        return self
