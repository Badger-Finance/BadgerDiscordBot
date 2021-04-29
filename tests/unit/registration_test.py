import asyncio
import boto3
from dotenv import load_dotenv
import logging
from moto import mock_sqs, mock_dynamodb2
import os
import pytest
import sys
import time

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

from honey_badger import BadgerBot

load_dotenv()

test_registration = {
    "discord_id": "123456789012345678",
    "discord_name": "test#0000",
    "wallet_address": "0xB1AdceddB2941033a090dD166a462fe1c2029484",
    "discourse": "test_user",
    "github": "test_user",
}

badger_bot = BadgerBot(
    discord_id=os.getenv("BOT_TOKEN_GENERAL"),
    github_pat=os.getenv("BADGER_SOURCECRED_PAT_TEST"),
    github_repo="btcookies/SourceCred",
    
)
badger_bot.sc.queue_name = "sourcecred-registration-requests"
badger_bot.sc.table_name = "sourcecred-registration"


async def mock_get_user_info(user_id):
    return "test_user"


async def mock_send_message(user, message):
    return True


class MockDiscordUser:
    def __init__(self, *args, **kwargs):
        self.id = test_registration.get("discord_id")
        self.display_name = test_registration.get("discord_name")


class MockDiscordMessage:
    def __init__(self, *args, **kwargs):
        self.author = MockDiscordUser()
        self.content = (
            "!register\n"
            "github: test_user\n"
            "discourse: test_user\n"
            "address: 0xB1AdceddB2941033a090dD166a462fe1c2029484\n"
        )


@pytest.fixture
def sqs():
    with mock_sqs():
        sqs_client = boto3.client("sqs")
        sqs_client.create_queue(QueueName="sourcecred-registration-requests")
        yield sqs_client


@pytest.fixture
def dynamodb():
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

        waivers_table = dynamodb_resource.Table("sourcecred-registration")
        waivers_table.update_item(
            Key={"discord_id": test_registration.get("discord_id")},
            ExpressionAttributeNames={
                "#G": "github_username",
                "#DS": "discourse_username",
                "#W": "wallet_address",
                "#DD": "discord_username",
            },
            ExpressionAttributeValues={
                ":g": test_registration.get("github"),
                ":ds": test_registration.get("discourse"),
                ":w": test_registration.get("wallet_address"),
                ":dd": test_registration.get("discord_name"),
            },
            UpdateExpression="SET #G=:g, #DS=:ds, #W=:w, #DD=:dd",
        )
        yield dynamodb_client, dynamodb_resource


def test_get_sourcecred_registration(monkeypatch):
    monkeypatch.setenv("SC_REGISTRATION_TABLE_NAME", "sourcecred-registration")
    monkeypatch.setenv("SC_REGISTRATION_QUEUE_NAME", "sourcecred-registration-requests")
    assert (
        badger_bot._get_sourcecred_registration_fields(MockDiscordMessage())
        == test_registration
    )


@pytest.mark.asyncio
async def test_send_user_registration_to_sqs_success(caplog, sqs, monkeypatch):
    badger_bot.get_user_info = mock_get_user_info
    badger_bot.send_message = mock_send_message
    with caplog.at_level(logging.INFO):
        await badger_bot._send_user_registration_to_sqs(test_registration)
        assert "Successfully sent registration message:" in caplog.text
        assert "Error submitting registration message." not in caplog.text
        assert "MD5OfMessageBody" in caplog.text


@pytest.mark.asyncio
async def test_register_user_for_sourcecred_already_registered(caplog, monkeypatch):
    monkeypatch.setattr(
        badger_bot, "_user_already_registered_sourcecred", lambda x: True
    )
    with caplog.at_level(logging.INFO):
        await badger_bot.register_user_for_sourcecred(MockDiscordMessage())
        assert "User already registered for SourceCred." in caplog.text


def test_user_already_registered_sourcecred(dynamodb, monkeypatch):
    assert (
        badger_bot._user_already_registered_sourcecred(
            test_registration.get("discord_id")
        )
        == True
    )
    assert badger_bot._user_already_registered_sourcecred("random") == False

