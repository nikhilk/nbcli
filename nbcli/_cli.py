# _cli.py
# Provides support for building command-line interfaces in Jupyter notebooks.

import argparse
import cStringIO
import genson
import jsonschema
import shlex
import sys
import types
import yaml
import IPython


class CommandLineParser(argparse.ArgumentParser):
  """A derived ArgumentParser for use in the IPython kernel and notebook environments.

  This implementation handles exits and errors appropriately without terminating the process.
  It also handles help/usage display to produce a Help payload that can be processed by the
  kernel to treat as help output.
  """
  def error(self, message):
    """Turns errors to exceptions, instead of exiting.
    """
    raise Exception(message)

  def exit(self, status=0, message=None):
    """Overrides exits with error messages (propagated via exceptions).
    """
    # Raise an error instead of exiting the process
    if status == 0 and message is None:
      # Exit after displaying help
      raise Exception('Help')
    else:
      raise Exception(message)

  def format_help(self):
    """Augment the default usage and flags help with information about expected content data.
    """
    help = super(CommandLineParser, self).format_help()
    help = help.replace('usage: ', 'usage:\n%')

    content = self.get_default('_content')
    if content is not None:
      help = help + '\ncontent: \n' + content.doc

    # Display help content as Help rather than execution output.
    IPython.core.page.page(help)
    return None

  def format_usage(self):
    return self.format_help()


class Command(object):
  """Represents a command within a command line.
  """
  def __init__(self, parser):
    self._parser = parser

  def add_argument(self, *args, **kwargs):
    self._parser.add_argument(*args, **kwargs)


class CommandGroup(object):
  """Represents a command group within a command line.

  Command groups contain (usually) two or more commands, and optionally contain arguments that
  apply to all commands within the group.
  """
  def __init__(self, parser):
    self._parser = parser
    self._subparsers = parser.add_subparsers()

  def add_command(self, name, handler, content=None, help=None):
    """Registers a command with the specified name and handler, and optional help string.

    The expected handler has the following signature:

      handler(args, env)

    The args contain the parsed arguments object. The env object is a dictionary representing the
    kernel session, and all values defined in the current session.

    If a content is specified, it is used to interpret the cell's content when the command is
    invoked.

    If content is a Function, the cell's body is interpreted as a YAML-formatted dictionary.
    The return value of the function is used to define the schema of the expected dictionary. It
    can be a list of objects, which are used to infer the schema, or be a jsonschema object. The
    docstring of the function is used to generate help content describing the expected dictionary.

    Otherwise content is interpreted as a plain text string. The value of content is used as
    the documentation of the expected content.

    For commands, handling content, the handler is expected to have the following signature:

      handler(args, content, env)

    Additionally, the argument values and values in a YAML-formatted content (if applicable), are
    automatically scanned for references to values within the kernel session. All $name occurrences
    are looked up and substituted. In addition to identifiers, the lookup also supports member
    references of the form $name.member_name.
    """
    command_parser = self._subparsers.add_parser(name=name, help=help)
    command_parser.set_defaults(_handler=handler)
    if content:
      if type(content) is types.FunctionType:
        content = YamlCommandContent(content)
      else:
        content = CommandContent(content)
      command_parser.set_defaults(_content=content)
    return Command(command_parser)

  def add_argument(self, *args, **kwargs):
    self._parser.add_argument(*args, **kwargs)


class CommandLineInterface(CommandGroup):
  """Represents the command line user experience.

  Each command line interface is associated with a name that is registered as an IPython magic.
  The magic is registered as both a line and cell magic. This allows commands to be split across
  multiple lines (just like on the terminal with '\' continuation).

  In addition, commands can optionally define a content spec, that is used to interpret the rest
  of the cell's content.
  """
  def __init__(self, name, description=None):
    parser = CommandLineParser(prog=name, description=description)
    super(CommandLineInterface, self).__init__(parser)

  def add_command_group(self, name, help=None):
    command_group_parser = self._subparsers.add_parser(name=name, help=help)
    return CommandGroup(command_group_parser)

  def execute(self, line, cell, ns):
    """Parses and executes the command specified within a cell in the context of a namespace.

    The namespace is usually the IPython session, providing access to variables defined within
    the current session.
    """
    args = None
    try:
      args, content = _parse_input(line, cell, ns, self._parser)
    except Exception as e:
      error = str(e)
      if error != 'Help':
        sys.stderr.write('Error: ' + error + '\n')
      return

    if content is not None:
      args._handler(args, content, env=ns)
    else:
      args._handler(args, env=ns)

  def register(self):
    """Registers the IPython magic.
    """
    cli = self
    ns = IPython.get_ipython().user_ns

    def magic_fn(line, cell=None):
      if not line:
        return
      cell = cell or ''
      cli.execute(line, cell, ns)

    IPython.core.magic.register_line_cell_magic(self._parser.prog)(magic_fn)


class CommandContent(object):
  """Represents a plain text command content.
  """
  def __init__(self, doc):
    self.doc = doc

  def parse(self, cell, ns):
    return cell


class YamlCommandContent(CommandContent):
  """Represents a YAML-formatted dictionary command content.
  """
  def __init__(self, yaml_spec_fn):
    super(YamlCommandContent, self).__init__(yaml_spec_fn.__doc__)

    schema = yaml_spec_fn()
    if schema is not None:
      if type(schema) is list:
        schema_generator = genson.Schema()
        for schema_example in schema:
          schema_generator.add_object(schema_example)
        schema = schema_generator.to_dict()
    self._schema = schema

  def parse(self, cell, ns):
    content = _expand_variables(ns, yaml.load(cell))

    if self._schema is not None:
      jsonschema.validate(content, self._schema)
    return content


def _expand_variables(ns, value):
  if isinstance(value, dict):
    return {k: _expand_variables(ns, v) for k, v in value.items()}
  elif isinstance(value, list):
    return [_expand_variables(ns, v) for v in value]
  elif isinstance(value, basestring) and value[0] == '$':
    name = value[1:]
    value = _lookup_value(ns, name)
    if value is None:
      raise Exception('Unable to find a valid value for "%s".' % name)
    return value
  else:
    return value

def _lookup_value(obj, name):
  for member in name.split('.'):
    if isinstance(obj, dict) and member in obj:
      obj = obj[member]
    elif isinstance(obj, types.ModuleType) and member in obj.__dict__:
      obj = obj.__dict__[member]
    else:
      return None
  return obj

def _parse_input(line, cell, ns, argparser):
  # First build the command-line which is made up of the first line, as well as lines from the
  # cell if the line preceeding it ends with a \ (i.e. normal command line behavior). The
  # remaining lines are considered to define the cell content.
  line = line.rstrip()
  if line[-1] == '\\':
    buffer = cStringIO.StringIO(cell)
    for l in buffer:
      line = line.rstrip('\\') + ' ' + l.rstrip('\n')
      if line[-1] != '\\':
        cell = buffer.read().rstrip()
        break

  # Split out args from the line using shlex to handle quotes and escapes. Additionally, replace
  # placeholders in command-line args.
  argv = _expand_variables(ns, shlex.split(line))
  args = argparser.parse_args(argv)

  content = None

  # If the args object includes a "_content" value, use it to parse the cell contents.
  if hasattr(args, '_content'):
    if not cell:
      raise Exception('Content must be specified for this command.')
    content = args._content.parse(cell, ns)
  else:
    if cell:
      raise Exception('Content is not supported for this command.')

  return args, content

