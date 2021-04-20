# badger-bot
Discord bot for Badger DAO channel.

### Proposed Architecture 

Hosted bot in container on EKS / ECS. DynamoDB storing active users. SQS queue containing pending activation requests. Lambda to consolidate activation requests, create actions, append to ledger, create PR.

General workflow will be user sends sourcecred registration message to bot, bot makes call to DynamoDB to see if user is active, if not creates activation action and sends to SQS. Every hour cloudwatch event triggers lambda to get all oustanding messages in SQS, appends actions to end of current ledger.json, makes and merges PR to master with updated ledger.json.