import asyncio
import boto3
from moto import mock_sqs, mock_dynamodb2
from dotenv import load_dotenv
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from honey_badger import BadgerBot

load_dotenv()


def setup_sqs():
    with mock_sqs():
        sqs_client = boto3.client("sqs")
        sqs_client.create_queue(QueueName="sourcecred-registration-requests")
        yield sqs_client


def setup_dynamodb():
    with mock_dynamodb2():
        dynamodb_client = boto3.client("dynamodb")
        dynamodb_client.create_table(
            TableName="sourcecred-registration",
            AttributeDefinitions=[
                {"AttributeName": "discord_id", "AttributeType": "S"},
            ],
            KeySchema=[{"AttributeName": "discord_id", "KeyType": "HASH"}],
        )

        dynamodb_resource = boto3.resource("dynamodb")

        yield dynamodb_client, dynamodb_resource


@setup_sqs
@setup_dynamodb
def main():
    pass


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    general_bot_client = BadgerBot(
        github_pat=os.getenv("BADGER_SOURCECRED_PAT_PROD"),
        github_repo="btcookies/SourceCred",
    )
    loop.create_task(general_bot_client.start(os.getenv("BOT_TOKEN_GENERAL")))

    loop.run_forever()
