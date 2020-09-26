# Echo example

## Description

This is a simple example of an HTTP API that listens to `GET` requests on `http://localhost:5000/echo` and responds by echoing the request's payload back to the caller.

## Instructions

From this directory run:

```sh
$ ./run.sh

Loading endpoints from serverless.yml config file...
Serving HTTP requests on 1 endpoint(s):
GET http://127.0.0.1:5000/echo -> echo/main.py
```

Now that your API server is running you can test it by running:

```sh
$ curl --location \
  --request GET 'http://127.0.0.1:5000/echo' \
  --header 'Content-Type: text/plain' \
  --data-raw 'anyone there?'

{"version": "2.0", "routeKey": "GET /echo", "rawPath": "/echo", "rawQueryString": "", "headers": {"host": "127.0.0.1:5000", "user-agent": "curl/7.64.1", "accept": "*/*", "content-type": "text/plain", "content-length": "13"}, "requestContext": {"accountId": "", "apiId": "", "domainName": "localhost", "domainPrefix": "", "http": {"method": "GET", "path": "/echo", "protocol": "HTTP/1.1", "sourceIp": "127.0.0.1", "userAgent": "curl/7.64.1"}, "requestId": "", "routeKey": "GET /echo", "stage": "$default", "time": "", "timeEpoch": 0}, "isBase64Encoded": false, "body": "anyone there?"}
```

And voilà! You should be able to see the payload that the `echo.py` Lambda function received with your request's body embedded in the payload's `body` attribute.
