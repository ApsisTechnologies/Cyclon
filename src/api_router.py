import os
from flask import Flask, request
from payload import build_payload
import lambda_utils
import logging

AUTH_HEADER = 'Authorization'
USER_AGENT = 'User-Agent'

class ApiRouter(Flask):
  '''
  Custom Flask webserver that creates routes based on passed endpoint configuration
  and responds to requests by routing the request to the corresponding lambda function via Docker.
  '''
  @staticmethod
  def __page_not_found(error):
    return 'Page not found', 404

  @staticmethod
  def __method_not_allowed(error):
    return 'Method not allowed', 405

  def __init__(
      self,
      name,
      endpoint_config,
      environment=None,
      layer_dir=None,
      docker_network_name=None
    ):
    super().__init__(import_name=name)

    # only print Flask errors
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    self.endpoint_config = endpoint_config
    self.docker_network_name = docker_network_name
    self.environment = environment
    self.layer_dir = layer_dir

    if self.layer_dir:
      self.layer_dir = os.path.abspath(layer_dir)

    self.errorhandler(404)(ApiRouter.__page_not_found)
    self.errorhandler(405)(ApiRouter.__method_not_allowed)

    # for each configured endpoint create a Flask route
    for api in self.endpoint_config:
      api_config = endpoint_config[api]
      self.route(
        api_config['path'],
        methods=[api_config['method']])(self.__route_request)

  def __route_request(self):
    '''
    Handles incoming requests, builds the message payload and invokes the corresponding Lambda
    function.
    '''
    params = {}
    for p in request.args:
      params[p] = request.args.get(p)

    # pass headers, converting header names to lowercase
    headers = {}
    for header in request.headers:
      headers[header[0].lower()] = header[1]

    user_agent = None
    if USER_AGENT in request.headers:
      user_agent = request.headers[USER_AGENT]

    payload = build_payload(
      route=request.path,
      method=request.method,
      user_agent=user_agent,
      source_ip=request.remote_addr,
      headers=headers,
      params=params if params else None,
      body=str(request.data, encoding='utf-8')
    )

    # TODO invoke corresponding Lambda function based on path
    if payload['routeKey'] not in self.endpoint_config:
      return 'Endpoint configuration not found', 500

    config = self.endpoint_config[payload['routeKey']]

    print('{}: Invoking function "{}"...'.format(payload['routeKey'], config['function']))

    response = lambda_utils.run_function(
      function_file_path=config['filepath'],
      payload=payload,
      layer_dir=self.layer_dir,
      docker_network_name=self.docker_network_name,
      environment=self.environment,
      handler_name=config['handler']
    )

    print('Lambda output:')
    print(response['stdout'])

    if response['exit_status'] != 0:
      return response['return_value'], 500

    status_code = response['return_value']['statusCode']
    headers = {}
    if 'headers' in response['return_value']:
      headers = response['return_value']['headers']

    body = ''
    if 'body' in response['return_value']:
      body = response['return_value']['body']

    return body, status_code, headers
