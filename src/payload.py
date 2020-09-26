import base64
import hmac
from hashlib import sha256
import json

'''
Lambda function payload utilities for AWS HTTP API payload v2.0.

Reference: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html#2.0
'''

AUTH_HEADER = 'authorization'
CONTENT_TYPE = 'content-type'
CONTENT_LENGTH = 'content-length'

def build_jwt(user_id, name=None, email=None, secret='default'):
  '''
  Builds a JWT with the provided user_id (as JWT's "sub" property), an optional name and signs it
  with the optional secret key.
  '''
  JWT_HEADER = {
    'alg': 'HS256',
    'typ': 'JWT'
  }

  jwt_payload = {
    'sub': user_id
  }

  if name:
    jwt_payload['name'] = name

  if email:
    jwt_payload['email'] = email

  # convert jwt header into a compact json string and encode it as url-safe base64
  jwt_header_str = json.dumps(JWT_HEADER, separators=(',', ':'))
  jwt_header_b64 = base64.urlsafe_b64encode(jwt_header_str.encode('ascii'))

  # remove header padding (ascii(61) == '=')
  while jwt_header_b64[-1] == 61:
    jwt_header_b64 = jwt_header_b64[:-1]

  # convert jwt payload into a compact json string and encode it as url-safe base64
  jwt_payload_str = json.dumps(jwt_payload, separators=(',', ':'))
  jwt_payload_b64 = base64.urlsafe_b64encode(jwt_payload_str.encode('ascii'))

  # remove payload padding (ascii(61) == '=')
  while jwt_payload_b64[-1] == 61:
    jwt_payload_b64 = jwt_payload_b64[:-1]

  # generate HMAC256 from header + '' + payload
  hmac_256 = hmac.new(
    key=secret.encode('ascii'),
    msg=jwt_header_b64 + b'.' + jwt_payload_b64,
    digestmod=sha256
  )

  signature = base64.urlsafe_b64encode(hmac_256.digest())

  # remove signature padding (ascii(61) == '=')
  while signature[-1] == 61:
    signature = signature[:-1]

  return str(jwt_header_b64 + b'.' + jwt_payload_b64 + b'.' + signature, encoding='utf-8')

def build_payload(
    route='/',
    method='GET',
    user_agent=None,
    source_ip=None,
    server_hostname=None,
    headers=None,
    params=None,
    body=None
  ):
  '''
  Builds a payload event object with the provided parameters.
  If auth is provided it will be interpreted as a Json Web Token and its JWT payload
  (not to be confused with the API payload which this function builds) will be included under
  requestContext:authorizer:jwt:claims object property.
  '''

  payload = json.loads(payload_template.format(
    ROUTE=route.strip(),
    METHOD=method.strip(),
    USER_AGENT=user_agent if user_agent else '',
    SOURCE_IP=source_ip if source_ip else '0.0.0.0',
    SERVER_HOST=server_hostname if server_hostname else 'localhost'
  ))

  # populate provided headers while converting header names to lowercase
  _headers = {}
  if headers:
    for header in headers:
      _headers[header.lower()] = headers[header]

  # add content-length header if missing
  if CONTENT_LENGTH not in _headers:
    _headers[CONTENT_LENGTH] = len(body) if body else 0

  # default content type
  if CONTENT_TYPE not in _headers:
    _headers[CONTENT_TYPE] = 'application/json'

  # populate headers
  for header in _headers:
    payload['headers'][header] = _headers[header]

  if body:
    payload['body'] = body

  # if authorization header is provided, include it along with decoded jwt payload
  if AUTH_HEADER in _headers:
    jwt = _headers[AUTH_HEADER]
    payload['headers'][AUTH_HEADER] = jwt
    payload['requestContext']['authorizer'] = {
      'jwt': {
        'claims': parse_jwt_payload(jwt)
      },
      'scopes': None
    }

  if params:
    rawQueryString = ''
    payload['queryStringParameters'] = {}
    for param in params:
      payload['queryStringParameters'][param] = params[param]
      rawQueryString += '{}={}&'.format(param.strip(), str(params[param]).strip())
    if rawQueryString:
      rawQueryString = rawQueryString[:-1]
    payload['rawQueryString'] = rawQueryString

  return payload

def build_authenticated_payload(user_id, authentication_header='Authorization', **kwargs):
  '''
  Builds payload using a generated JWT based on specified user_id and adds the corresponding
  authentication header (default header value: 'Authorization').
  '''
  if 'headers' not in kwargs:
    kwargs['headers'] = {}

  kwargs['headers'][authentication_header] = build_jwt(user_id)
  return build_payload(**kwargs)

def parse_jwt_payload(jwt):
  '''
  Parses the provided JWT's payload, decodes and returns it as a Python object.
  '''
  tokens = jwt.split('.')
  if len(tokens) != 3:
    raise ValueError('Invalid JWT: {}'.format(jwt))

  payload = tokens[1]
  # add padding if necessary to decode base64 payload correctly
  for _ in range(len(payload) % 4):
    payload += '='

  return json.loads(base64.b64decode(payload))

payload_template = '''\
{{
  "version": "2.0",
  "routeKey": "{METHOD} {ROUTE}",
  "rawPath": "{ROUTE}",
  "rawQueryString": "",
  "headers": {{
  }},
  "requestContext": {{
    "accountId": "",
    "apiId": "",
    "domainName": "{SERVER_HOST}",
    "domainPrefix": "",
    "http": {{
      "method": "{METHOD}",
      "path": "{ROUTE}",
      "protocol": "HTTP/1.1",
      "sourceIp": "{SOURCE_IP}",
      "userAgent": "{USER_AGENT}"
    }},
    "requestId": "",
    "routeKey": "{METHOD} {ROUTE}",
    "stage": "$default",
    "time": "",
    "timeEpoch": 0
  }},
  "isBase64Encoded": false
}}
'''
