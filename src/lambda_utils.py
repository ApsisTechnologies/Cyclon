import os
import subprocess
import json
import utils

NODE_IMAGE_NAME = 'lambci/lambda:nodejs12.x'
PYTHON_IMAGE_NAME = 'lambci/lambda:python3.7'
IMAGE_TASK_DIR = '/var/task'
IMAGE_LAYER_DIR = '/opt'

def run_function(
    function_file_path,
    payload=None,
    layer_dir=None,
    docker_network_name=None,
    environment=None,
    handler_name='handler'
  ):
  '''
  Runs the specified Lambda function and returns an object containing information
  describing the function's status output. The function can receive an optional
  payload object which will be serialized and passed as the function's first parameter.
  If layer_dir is specified the path will be mounted as the function's (single) layer.
  Specifying docker_network allows the function to connect to said network to access
  services connected to it.
  If environment is passed, the values contained will be passed as environment
  variables which the function's runtime will be able to access.
  The function's entrypoint name can be configure by specifying handler_name (default: 'handler').

  Return type (dict):
  {
    'raw_output': Raw string with the function's return value if any>.
    'return_value': A Python type with the function's return value(s).
    'exit_status': A number indicating the function's exit code (zero means success).
    'stdout': The full function output as captured via stdout.
    'error_type': The (unhandled) exception type that was caught when the function was run.
    'error_message': The error message that was generated, if any.
    'stack_trace': The stack trace produced by the unhandled error, if any.
  }
  '''
  # validate function directory exists
  if not os.path.exists(function_file_path) and not os.path.isfile(function_file_path):
    raise FileNotFoundError(
      'Function \'{}\' not found or is not a file'.format(function_file_path)
    )

  function_name = os.path.splitext(os.path.basename(function_file_path))[0]
  function_dir = os.path.dirname(function_file_path)

  runtime = None
  function_extension = os.path.splitext(function_file_path)[1]
  if function_extension == '.js':
    runtime = 'node'
  elif function_extension == '.py':
    runtime = 'python'
  else:
    raise TypeError(
      'Cannot find matching Lambda runtime for function extension "{}"'.format(function_extension)
    )

  # the Docker Lambda images we currently support
  IMAGES = {
    'node': NODE_IMAGE_NAME,
    'python': PYTHON_IMAGE_NAME
  }

  # build Docker command:
  cmd = 'docker run --rm -it -v {}:{}:ro,delegated'.format(function_dir, IMAGE_TASK_DIR)

  # mount layer if present
  if layer_dir:
    layer_dir = os.path.abspath(layer_dir)
    if not os.path.exists(layer_dir) and not os.path.isdir(layer_dir):
      raise FileNotFoundError(
        'Layer directory \'{}\' not found or is not a directory'.format(layer_dir)
      )
    cmd += ' -v {}:{}:ro,delegated'.format(layer_dir, IMAGE_LAYER_DIR)

  # pass function environment variables
  if environment:
    for key in environment:
      cmd += ' -e {}=\'{}\''.format(key, environment[key])

  # pass network if any to allow this container to access other services
  if docker_network_name:
    cmd += ' --network {}'.format(docker_network_name)

  # configure lambda Docker image and function entrypoint
  cmd += ' {} {}.{}'.format(IMAGES[runtime], function_name, handler_name)

  if payload:
    cmd += ' \'{}\''.format(json.dumps(payload))

  # run lambda
  retcode = 0
  stdout = ''
  try:
    output = utils.run_cmd(cmd)
    retcode = output.returncode
    stdout = output.stdout.decode('utf-8')
  except subprocess.CalledProcessError as error:
    retcode = error.returncode
    stdout = error.stdout.decode('utf-8')

  # last line is a string returned by the function runtime, if any
  function_output = stdout.splitlines()[-1]
  ret_value = json.loads(function_output)
  response = {
    'raw_output': function_output if function_output != 'null' else None,
    'return_value': ret_value,
    'exit_status': retcode,
    'stdout': stdout
  }

  if ret_value:
    response['error_type'] = ret_value['errorType'] if 'errorType' in ret_value else None
    response['error_message'] = ret_value['errorMessage'] if 'errorMessage' in ret_value else None
    response['stack_trace'] = ret_value['stackTrace'] if 'stackTrace' in ret_value else None

  return response
