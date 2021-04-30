import asyncio
import boto3
from dotenv import load_dotenv
import json
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
        sqs_resource = boto3.resource("sqs")
        yield sqs_client, sqs_resource


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


@pytest.fixture
def badger_bot(sqs, dynamodb):
    badger_bot = BadgerBot(
        discord_id=os.getenv("BOT_TOKEN_GENERAL"),
        github_pat=os.getenv("BADGER_SOURCECRED_PAT_TEST"),
        github_repo="btcookies/SourceCred",
    )

    yield badger_bot


def test_get_sourcecred_registration(badger_bot, monkeypatch):
    monkeypatch.setenv("SC_REGISTRATION_TABLE_NAME", "sourcecred-registration")
    monkeypatch.setenv("SC_REGISTRATION_QUEUE_NAME", "sourcecred-registration-requests")
    assert (
        badger_bot._get_sourcecred_registration_fields(MockDiscordMessage())
        == test_registration
    )


@pytest.mark.asyncio
async def test_send_user_registration_to_sqs_success(badger_bot, caplog, monkeypatch):
    badger_bot.get_user_info = mock_get_user_info
    badger_bot.send_message = mock_send_message
    with caplog.at_level(logging.INFO):
        await badger_bot._send_user_registration_to_sqs(test_registration)
        assert "Successfully sent registration message:" in caplog.text
        assert "Error submitting registration message." not in caplog.text
        assert "MD5OfMessageBody" in caplog.text


@pytest.mark.asyncio
async def test_submit_sourcecred_user_registration_already_registered(
    badger_bot, caplog, monkeypatch
):
    badger_bot.get_user_info = mock_get_user_info
    monkeypatch.setattr(
        badger_bot, "_user_already_registered_sourcecred", lambda x: True
    )
    with caplog.at_level(logging.INFO):
        await badger_bot.submit_sourcecred_user_registration(MockDiscordMessage())
        assert "User already registered for SourceCred." in caplog.text


def test_user_already_registered_sourcecred(badger_bot, dynamodb, monkeypatch):
    assert (
        badger_bot._user_already_registered_sourcecred(
            test_registration.get("discord_id")
        )
        == True
    )
    assert badger_bot._user_already_registered_sourcecred("random") == False


def test_get_outstanding_registration_messages(badger_bot, sqs, monkeypatch):
    message = "test message"
    sqs_queue_url = sqs[0].get_queue_url(QueueName="sourcecred-registration-requests")[
        "QueueUrl"
    ]

    msg = sqs[0].send_message(QueueUrl=sqs_queue_url, MessageBody=message)

    assert len(badger_bot._get_outstanding_registration_messages()) == 1

    for i in range(20):
        msg = sqs[0].send_message(QueueUrl=sqs_queue_url, MessageBody=message)

    assert len(badger_bot._get_outstanding_registration_messages()) == 20


def test_get_unique_registrations(badger_bot, sqs, monkeypatch):
    sqs_queue_url = sqs[0].get_queue_url(QueueName="sourcecred-registration-requests")[
        "QueueUrl"
    ]

    for _ in range(21):
        sqs[0].send_message(
            QueueUrl=sqs_queue_url, MessageBody=json.dumps(test_registration)
        )
    registrations = badger_bot._get_outstanding_registration_messages()

    unique_registrations = badger_bot._get_unique_registrations(registrations)

    assert len(unique_registrations) == 1
    assert unique_registrations == {
        "123456789012345678": {
            "discord_id": "123456789012345678",
            "discord_name": "test#0000",
            "discourse": "test_user",
            "github": "test_user",
            "wallet_address": "0xB1AdceddB2941033a090dD166a462fe1c2029484",
        }
    }

    unprocessed_messages = badger_bot._get_outstanding_registration_messages()
    assert len(unprocessed_messages) == 0

    unique_registrations = badger_bot._get_unique_registrations(unprocessed_messages)
    assert len(unique_registrations) == 0


def test_mark_users_activated(badger_bot, sqs, dynamodb, monkeypatch):
    sqs_queue_url = sqs[0].get_queue_url(QueueName="sourcecred-registration-requests")[
        "QueueUrl"
    ]

    for _ in range(21):
        sqs[0].send_message(
            QueueUrl=sqs_queue_url, MessageBody=json.dumps(test_registration)
        )
    registrations = badger_bot._get_outstanding_registration_messages()

    unique_registrations = badger_bot._get_unique_registrations(registrations)
    activated_discord_ids = [discord_id for discord_id in unique_registrations.keys()]

    badger_bot._mark_users_activated(activated_discord_ids, unique_registrations)
    table = dynamodb[1].Table("sourcecred-registration")
    item = table.get_item(Key={"discord_id": test_registration.get("discord_id")}).get(
        "Item"
    )

    assert item != None
    assert item == {
        "discord_id": "123456789012345678",
        "discord_username": "test#0000",
        "discourse_username": "test_user",
        "github_username": "test_user",
        "wallet_address": "0xB1AdceddB2941033a090dD166a462fe1c2029484",
    }
