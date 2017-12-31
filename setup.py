# setup.py
#

import setuptools

setuptools.setup(
  name='notebook-cli',
  version='0.1',
  author='Nikhil Kothari',
  description='Enables building command-line interfaces in Jupyter notebooks using IPython magics.',
  license='BSD',
  keywords='cli commandline jupyter interactive argparse yaml ipython',
  url='https://github.com/nikhilk/nbcli',
  packages=[
    'nbcli'
  ],
  install_requires = [
    'argparse',
    'genson',
    'ipykernel',
    'jsonschema',
    'pyyaml'
  ],
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Framework :: IPython',
    'Framework :: Jupyter',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2.7',
    'License :: OSI Approved :: Apache Software License'
  ],
)

