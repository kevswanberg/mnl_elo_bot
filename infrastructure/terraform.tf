terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

terraform {
  backend "remote" {
    organization = "mnl_elo_bot"

    workspaces {
      name = "mnl_elo_bot_deploy"
    }
  }
}

provider "aws" {
  region  = var.region
  profile = "default"
}

resource "aws_lambda_function" "mnl_elo_bot" {
  function_name = "MNL_elo_bot"
  package_type  = "Image"
  image_uri     = "842462664636.dkr.ecr.us-east-1.amazonaws.com/mnl_elo_bot:${var.image_tag}"

  role = aws_iam_role.lambda_exec.arn
  environment {
    variables = {
      SLACK_CLIENT_ID = var.slack_client_id,
      IMGUR_CLIENT_ID = var.imgur_client_id
    }
  }
  timeout = 10
}

# IAM role which dictates what other AWS services the Lambda function
# may access.
resource "aws_iam_role" "lambda_exec" {
  name = "mnl_elo_bot_lambda_role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF

}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mnl_elo_bot.function_name
  principal     = "apigateway.amazonaws.com"

  # The "/*/*" portion grants access from any method on any resource
  # within the API Gateway REST API.
  source_arn = "${aws_api_gateway_rest_api.mnl_elo_bot.execution_arn}/*/*"
}

output "base_url" {
  value = aws_api_gateway_deployment.mnl_elo_bot.invoke_url
}
