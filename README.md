# Cyclon: Rapid cloud API development framework

## Description

Cyclon is a framework for rapid development and integration of cloud APIs. It allows running cloud functions and their corresponding cloud infrastructure fully locally, allowing you to design and iterate your cloud-based apps much faster.

Cyclon is written in [Python](https://www.python.org/) ❤️.

## Main benefits

- It avoids having to redeploy every minor code change (as well as potentially breaking changes) before you can start testing your app; only redeploy once your code is stable enough and you're happy with it.

- It makes you and your team more producive by encouraging experimentation: design, develop, break stuff, and test without being afraid of breaking your existing deployment.

- Since development happens locally it reduces the cost of developing and testing against real cloud infrastructure.

- It supports all [AWS Lambda runtimes](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html).

## Quick start

Try one of the included examples by running:

- `git clone git@github.com:ApsisTechnologies/Cyclon.git`
- `cd Cyclon/examples/echo`
- `./run.sh`

Each example comes with a `README` file for an explanation of what it does.

## How it works

When you run Cyclon the following happens:

1. It reads your **existing [Serverless](https://www.serverless.com/) project configuration** and extracts your Lambda functions' configuration along with their corresponding HTTP API endpoints.
1. It creates and **sets up your project's infrastructure** via Docker containers.
1. It spins up an HTTP API server that mimicks AWS API Gateway and **listens for incoming API requests**.
1. It serves incoming requests by **invoking your Lambda functions** (via [Docker](https://www.docker.com/)) and **forwards the incoming request to your function code**.
1. Cyclon parses your function's output after it runs and **returns the result back to the caller** exactly in the same way that AWS API Gateway would.

As you can see, the exact same code you write for your cloud functions can be tested locally, thus making it much easier to develop and test your web and mobile apps.

You can adapt Cyclon to your own infrastructure by creating a new configuration based on an existing example or just creating your own from scratch.

## Dependencies

You'll need the following tools installed before you can run Cyclon:

- [Serverless framework](https://www.serverless.com/)
- [Python 3](https://www.python.org/)
- [Flask](https://palletsprojects.com/p/flask/)
- [Docker](https://www.docker.com/)

If they are not installed on your system Cyclon will politely remind you with an error message letting you know which ones are missing.

## Limitations

Cyclon is very new and the result of developing real-world products and so it's pretty opinionated. As such, it also comes with several limitations.
 AWS
Below is a list with some of them:

- It only targets AWS-flavored APIs, no other cloud providers are supported at the moment.
- It works with AWS' [HTTP APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html) (with [payload v2.0](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html#2.0) to be precise). They are faster, cheaper and simpler REST APIs.
- It does not currently create cloud resources for you (buckets, DynamoDB tables, SNS topics, etc). You may need to script that yourself (which is pretty easy to do). We might add this in the near future though.
- It expects you to setup your Serverless function configuration through separate configuration files (see examples), which is the more flexible, scalable approach.
- It doesn't aim to help with deployments but it makes every effort to ensure that the code you run locally is the same code you run on the cloud (i.e. avoiding writing stuff like `ifenv == 'PROD' then do this else do that`).
