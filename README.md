# badger-bot
Discord bot for Badger DAO channel.

### Proposed Architecture 

Hosted bot in container on EKS / ECS. DynamoDB storing active users. SQS queue containing pending activation requests. Lambda to consolidate activation requests, create actions, append to ledger, create PR.

General workflow will be user sends sourcecred registration message to bot, bot makes call to DynamoDB to see if user is active, if not creates activation action and sends to SQS. Every hour cloudwatch event triggers lambda to get all oustanding messages in SQS, appends actions to end of current ledger.json, makes and merges PR to master with updated ledger.json.

### Source Code
#### sourcecred.py
This file hosts the SourceCredManager class which is responsible for all reads and writes to the SourceCred instance.

#### honey_badger.py
This file hosts the BadgerBot class which contains the functions and commands supported by the general Badger Discord bot. Currently there is only one supported command, `!register`, which enrolls a user in the Badger SourceCred Kudos earning program if they are not already enrolled. This command requires the bot to make a call to DynamoDB to check if the user has already been registered, sending a Discord message via DM if they have. If the user has not yet been registered, it will process their registration information and submit it to an SQS queue to be processed in bulk every hour via a separate lambda. This design decision was made to consolidate registration requests in order to update the `ledger.json` file that acts as SourceCred's database via GitHub commit in bulk.

#### price_bot.py
This file represents a generic price Discord bot that will update its Discord name and activity with the price and market cap of a given token. The `sett_bot.py` and `digg_bot.py` are extensions of this class specific to Badger tokens that require more unique information to be displayed.

### How to run
To run the bots locally you can invoke the script you want using the following steps. There are currently two scripts available, `run_price_bots.py` which runs the BADGER, DIGG, bDIGG, and bBADGER bots. You can adapt this script to run bots for your token equivalent. The `run_honey_badger.py` script will run the bot that handles SourceCred registration. This bot requires an SQS queue and a DynamoDB table to be running in order to operate.
1. `pip install -r requirements.txt`
2. `python scripts/<insert_script_name>`

Docker updates coming soon.