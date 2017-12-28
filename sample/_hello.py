# _hello.py
# Declares a simple command.

def hello(args, env):
  print 'Hello World!'

def load(cli):
  cli.add_command('hello', hello, help='Simple top-level command')

