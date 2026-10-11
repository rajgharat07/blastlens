resource "aws_sqs_queue" "checkout_events" {
  name = "checkout-events"
}

resource "aws_lambda_function" "notify" {
  function_name = "notify-worker"
  role          = "arn:aws:iam::123456789012:role/demo"
  handler       = "index.handler"
  runtime       = "python3.12"
  filename      = "notify.zip"

  depends_on = [
    aws_sqs_queue.checkout_events
  ]
}
