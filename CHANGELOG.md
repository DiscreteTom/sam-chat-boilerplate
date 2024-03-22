# CHANGELOG

## v0.1.4

Fix: skip `json.loads` for `event['body']`.

## v0.1.3

Fix: `body` in `AsyncLambdaIntegrationRequestTemplates` should be `$input.body` so we don't need to escape anything, and quotes in the input will work nicely.

## v0.1.2

Fix: the default route should have a route response instead of an integration response.

## v0.1.1

Fix: `body` in `AsyncLambdaIntegrationRequestTemplates` should be `$input.body.replaceAll('"', '\"')`.

## v0.1.0

The initial release.
