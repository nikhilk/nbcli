# __init__.py
# Declaration of the nbcli module.

from _cli import CommandLineInterface

def create(name, modules, description=None):
  """A helper function to create a CommandLineInterface along with its commands.

  This registers a kernel '%magic' handler, using the specified name that supports both
  single line and multi-line mode declaration.

  The CLI is built out of one or more modules. Each module is expected to contain a 'load' method
  as follows:

     def load(cli):
       # Use specified CommandLineInterface to add command groups and/or commands.
       ...

  Command arguments can be specified on the first line or split across multiple lines (separated
  by a trailing '\') in a notebook cell. The body of the cell can contain command content, either
  plain text, or YAML, which is parsed into an object.

  Command arguments and values in the YAML can be specified as placeholders whose values are
  initialized to variables defined in the notebook environment.

  Args:
    name: The name of the command line interface.
    modules: The list of modules that are used to build the CLI.
    description: An optional description of the CLI.
  """
  cli = CommandLineInterface(name, description=description)
  for m in modules:
    load_cli_fn = m.__dict__['load']
    load_cli_fn(cli)

  cli.register()

