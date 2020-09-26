'''
System utilities.
'''

import json
import os
import subprocess

COLORS = {
  'red': '\033[91m',
  'green': '\033[92m',
  'yellow': '\033[93m',
  'blue': '\033[94m',
  'purple': '\033[95m',
  'cyan': '\033[96m',
  'gray': '\033[97m'
}

def color(text, color_name='red'):
  '''
  Returns colored text by wrapping it in the corresponding ANSI escape sequences.
  '''
  reset_color = '\033[00m'

  if color_name not in COLORS:
    raise Exception('Invalid color "{}". Please pass one of {}'.format(color_name, COLORS.keys()))

  return '{}{}{}'.format(COLORS[color_name], text, reset_color)

def list_directories(path):
  '''
  Returns a list containing all the directories found at the provided path.
  '''
  return [dir for dir in os.listdir(path) if os.path.isdir(os.path.join(path, dir))]

def list_files(path, predicate=None, recursive=False):
  '''
  Returns a list containing all files found at the provided path. If recursive
  is True then subdirectories wull be scanned as well. If predicate is specified
  it will be used to filter out the paths included.
  '''
  if not predicate:
    predicate = lambda _: True

  def recursive_list_files(files, base_path):
    for p in os.listdir(base_path):
      abs_path = os.path.abspath(os.path.join(base_path, p))
      if os.path.isdir(abs_path):
        recursive_list_files(files, abs_path)
      elif os.path.isfile(abs_path) and predicate(abs_path):
        files.append(abs_path)

  path = os.path.abspath(path)
  if recursive:
    files = []
    recursive_list_files(files, path)
    return files

  return [
    os.path.abspath(p) for p in os.listdir(path) \
      if os.path.isfile(os.path.join(path, p)) and predicate(os.path.abspath(p))
  ]

def run_cmd(cmd):
  '''
  Runs the provided command, returning the result of the run.
  '''
  return subprocess.run(cmd, capture_output=True, shell=True, check=True)

def read_env_file(env_file_path):
  '''
  Parses the provided environment file and returns a
  dictionary populated with the variables found in it.
  '''
  env = {}
  with open(env_file_path) as f:
    for line in f.readlines():
      line = line.strip()
      if line.startswith('#') or not line:
        continue
      var = line.split('=', 1)
      if len(var) != 2:
        raise Exception('incorrect environment variable format: "{}"'.format(line))
      env[var[0].strip()] = var[1].strip()
  return env

def load_env_file(env_file_path):
  '''
  Parses the provided environment file and sets all the environment variables found in it.
  '''
  env = read_env_file(env_file_path)
  for var in env:
    os.environ[var] = env[var]

def load_json(file_path):
  try:
    file_path = os.path.abspath(file_path)
    return json.load(open(file_path, 'r'))
  except json.decoder.JSONDecodeError as error:
    raise SyntaxError(
      'Error parsing json file \'{}\': "{}"'.format(file_path, str(error))
    ) from None

def print_json(obj, indent=2):
  print(json.dumps(obj, indent=indent, default=str))
