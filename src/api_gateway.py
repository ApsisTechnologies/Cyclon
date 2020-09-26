#!/usr/bin/env python3

'''
API Gateway server.
'''

import getopt
import json
import os
import sys
import traceback
from subprocess import CalledProcessError
from flask_cors import CORS

from api_router import ApiRouter
import utils

def check_dependencies():
  '''
  Checks that tool dependencies are met
  '''
  deps = [
    {'name': 'Docker', 'cmd': 'docker --version'},
    {'name': 'Flask', 'cmd': 'flask --version'},
    {'name': 'Serverless framework', 'cmd': 'sls --version'},
    {'name': 'Python', 'cmd': 'python3 --version'}
  ]

  deps_are_satisfied = True
  for dep in deps:
    try:
      utils.run_cmd(dep['cmd'])
    except CalledProcessError:
      print('Missing dependency "{}". Please install it and retry.'.format(dep['name']))
      deps_are_satisfied = False

  return deps_are_satisfied

def usage(message=None):
  if message:
    print(message + '\n')
  else:
    print('''\
HTTP API Server

Flask-based web server that handles HTTP API requests and routes them to Lambda functions based on Serverless configuration.

Note: This script assumes as a convention that Lambda function source code is located in "<base function dir>/<function name>/<handler name>[.py|.js]".

Usage: {CMD} [OPTIONS]

Options:

-f | --functions <functions dir>:   Base directory where Lambda functions are located. Default: "<current dir>/functions".
-p | --port <server port>:          Port the server will listen for API calls. Default: 5000.
-s | --sls <sls config file path>:  Serverless configuration file path. Default: "<current dir>/serverless.yml".
-e | --env <environment file path>: Path to the file containing environment variables passed to Lambda function. Default: "<current dir>/.env".
-l | --layer <layer dir>:           Path to directory that will be mounted as Lambda function layer.
-n | --network <docker network>:    The name of the Docker network Lambda functions should be created in.
-h | --help:                        Print this help message.
-v | --verbose:                     Enable verbose output.

Example (simple):

{CMD} --functions ./my_function_dir

Example (advanced):

{CMD} --functions ./my_function_dir --port 4004 --sls .serverless --env .env --network default
'''.format(CMD=os.path.basename(sys.argv[0])))

  sys.exit(1 if message else 0)


def extract_http_api_endpoints(sls_config_file_path, functions_base_dir):
  '''
  Parses generated Serverless configuration file (i.e. the one resulting from running "sls package"
  as opposed to the regular Serverless configuration yaml file) and returns a dictionary describing
  the configured AWS HTTP API endpoints, along with the path to the Lambda function handlers.
  '''

  PROVIDER_TAG = 'provider'
  FUNCTIONS_TAG = 'functions'
  RUNTIME_TAG = 'runtime'
  HANDLER_TAG = 'handler'
  EVENTS_TAG = 'events'
  HTTP_API_TAG = 'httpApi'
  HTTP_API_METHOD_TAG = 'method'
  HTTP_API_PATH_TAG = 'path'

  DUMP_CONFIG_CMD = 'cd "{}"; sls print --format json --config "{}"'.format(
    os.path.dirname(sls_config_file_path),
    os.path.basename(sls_config_file_path)
  )
  CONFIG = json.loads(utils.run_cmd(DUMP_CONFIG_CMD).stdout)

  apis = {}

  default_service_runtime = None
  if RUNTIME_TAG in CONFIG[PROVIDER_TAG]:
    default_service_runtime = CONFIG[PROVIDER_TAG][RUNTIME_TAG]

  for FUNCTION in CONFIG[FUNCTIONS_TAG]:
    FUNCTION_NAME = list(FUNCTION)[0]
    FUNCTION_CONFIG = FUNCTION[FUNCTION_NAME]
    runtime = default_service_runtime
    if RUNTIME_TAG in FUNCTION_CONFIG:
      runtime = FUNCTION_CONFIG[RUNTIME_TAG]

    if not runtime:
      raise Exception(
        'Function "{}" runtime not specified, please configure a runtime for it.'.format(
          FUNCTION_NAME
        )
      )

    if runtime.startswith('python'):
      EXT = '.py'
    elif runtime.startswith('nodejs'):
      EXT = '.js'
    else:
      # skip functions with unsupported runtimes
      print(
        'WARNING: unsupported runtime: "{}". Skipping function "{}"'.format(runtime, FUNCTION_NAME),
        file=sys.stderr
      )
      continue

    if HANDLER_TAG not in FUNCTION_CONFIG:
      raise Exception('Function "{}" handler config not found.'.format(FUNCTION_NAME))

    HANDLER = FUNCTION_CONFIG[HANDLER_TAG].split('.')
    if len(HANDLER) != 2:
      raise Exception('Invalid handler config for function "{}"'.format(FUNCTION_NAME))

    HANDLER_FILE_NAME = HANDLER[0]
    HANDLER_NAME = HANDLER[1]
    FUNCTION_FILE_PATH = os.path.join(
      os.path.abspath(functions_base_dir),
      FUNCTION_NAME + '/' + HANDLER_FILE_NAME + EXT
    )

    if not os.path.exists(FUNCTION_FILE_PATH):
      raise Exception('Handler function file path not found: "{}"'.format(FUNCTION_FILE_PATH))

    if EVENTS_TAG in FUNCTION_CONFIG:
      HTTP_API_EVENTS = [e[HTTP_API_TAG] for e in FUNCTION_CONFIG[EVENTS_TAG] if HTTP_API_TAG in e]
      for http_event in HTTP_API_EVENTS:
        RESOURCE_ID = http_event[HTTP_API_METHOD_TAG] + ' ' + http_event[HTTP_API_PATH_TAG]

        if RESOURCE_ID in apis:
          raise Exception('Duplicated HTTP method: {}'.format(RESOURCE_ID))

        apis[RESOURCE_ID] = {
          'function': FUNCTION_NAME,
          'method': http_event[HTTP_API_METHOD_TAG],
          'path': http_event[HTTP_API_PATH_TAG],
          'runtime': runtime,
          'handler': HANDLER_NAME,
          'filepath': FUNCTION_FILE_PATH
        }

  return apis


if __name__ == '__main__':
  try:
    opts, args = getopt.getopt(
      args=sys.argv[1:],
      shortopts='f:p:s:e:l:n:vh',
      longopts=[
        'functions=',
        'port=',
        'sls=',
        'env=',
        'layer=',
        'network=',
        'verbose',
        'help'
      ]
    )
  except getopt.GetoptError as error:
    usage('Invalid arguments: {}'.format(error))

  SLS_CONFIG_FILE_PATH = os.path.join(os.getcwd(), 'serverless.yml')
  FUNCTIONS_DIR = os.path.join(os.getcwd(), 'functions')
  PORT = 5000
  HOSTNAME = '127.0.0.1'
  ENV_FILE_PATH = None
  LAYER_DIR = None
  DOCKER_NETWORK_NAME = None

  for opt, arg in opts:
    if opt in ('-f', '--functions'):
      FUNCTIONS_DIR = arg
    elif opt in ('-p', '--port'):
      PORT = arg
    elif opt in ('-s', '--sls'):
      SLS_CONFIG_FILE_PATH = arg
    elif opt in ('-e', '--env'):
      ENV_FILE_PATH = arg
    elif opt in ('-l', '--layer'):
      LAYER_DIR = arg
    elif opt in ('-n', '--network'):
      DOCKER_NETWORK_NAME = arg
    elif opt in ('-h', '--help'):
      usage()
    else:
      usage('Invalid option \'{}\''.format(opt))

  SLS_CONFIG_FILE_PATH = os.path.abspath(SLS_CONFIG_FILE_PATH)
  if not os.path.exists(SLS_CONFIG_FILE_PATH):
    print('Serverless configuration file not found: \'{}\''.format(SLS_CONFIG_FILE_PATH))
    sys.exit(1)

  environment = None
  if ENV_FILE_PATH:
    if not os.path.exists(ENV_FILE_PATH):
      print('Environment file "{}" not found'.format(ENV_FILE_PATH))
      sys.exit(1)

    # load environment variables from file
    environment = utils.read_env_file(ENV_FILE_PATH)

  if LAYER_DIR:
    LAYER_DIR = os.path.abspath(LAYER_DIR)
    if not os.path.exists(LAYER_DIR) or not os.path.isdir(LAYER_DIR):
      print('Invalid layer directory: "{}"'.format(LAYER_DIR))
      sys.exit(1)

  # check that dependency tools are installed
  if not check_dependencies():
    sys.exit(1)

  try:
    print('Loading endpoints from {} config file...'.format(os.path.relpath(SLS_CONFIG_FILE_PATH)))

    # extract HTTP API endpoints
    endpoint_config = extract_http_api_endpoints(SLS_CONFIG_FILE_PATH, FUNCTIONS_DIR)

    if not endpoint_config:
      print(
        'No HTTP API endpoints were found. Please make sure there\'s at least one function '
        'with one HTTP API event configured.'
      )
      sys.exit(1)

    print('Serving HTTP requests on {} endpoint(s):'.format(len(endpoint_config.keys())))
    for api_resource in endpoint_config:
      api = endpoint_config[api_resource]
      print('{} {} -> {}'.format(
        utils.color(api['method'], 'blue'),
        utils.color('http://' + HOSTNAME + ':' + str(PORT) + api['path'], 'cyan'),
        os.path.relpath(api['filepath'])
      ))

    # run custom Flask server
    router = ApiRouter(
      name='API Gateway server',
      endpoint_config=endpoint_config,
      environment=environment,
      layer_dir=LAYER_DIR,
      docker_network_name=DOCKER_NETWORK_NAME
    )
    CORS(router)

    router.run(host=HOSTNAME, port=PORT, debug=False, )

  except Exception as error:
    print('Error: {}'.format(error), file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
