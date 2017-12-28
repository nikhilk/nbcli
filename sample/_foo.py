# _foo.py
# Declares commands within a commnd group.

def foo_spec():
  """The content contains a specificationof the foo resource to create.

  name: name-of-the-resource
  xyz: something-else
  """
  return [
    {'name': ''},
    {'name': '', 'xyz': 123}
  ]

def create(args, content, env):
  print 'Creating a foo with the following specification...'

  print content

  name = content['name']
  env[name] = {'type': 'foo', 'xyz': content.get('xyz', 123)}

def delete(args, env):
  print 'Deleting a foo named "%s"' % args.name
  del env[args.name]

def load(cli):
  foos = cli.add_command_group('foo')
  foos.add_argument('--environment', metavar='env', type=str,
                    help='The name of the environment',
                    default='default')

  foos.add_command('create', create, content=foo_spec,
                   help='Creates a foo resource')

  delete_command = foos.add_command('delete', delete, help='Deletes a foo resource')
  delete_command.add_argument('--name', metavar='name', required=True, type=str,
                              help='The name of the resource')

