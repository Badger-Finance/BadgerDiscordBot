import boto3
import discord
from dotenv import load_dotenv
from discord.ext import commands, tasks
import json
import logging
import math
import os
import requests
from sourcecred import SourceCredManager

load_dotenv()

SC_REGISTRATION_TABLE_NAME = os.getenv("SC_REGISTRATION_TABLE_NAME")
SC_REGISTRATION_QUEUE_NAME = os.getenv("SC_REGISTRATION_QUEUE_NAME")


class BadgerBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = logging.getLogger("honey-badger-bot")
        self.logger.setLevel(logging.INFO)
        self.discord_id = kwargs.get("discord_id")
        self.sc = SourceCredManager(
            kwargs.get("github_pat"),
            kwargs.get("github_repo"),
            queue_name=SC_REGISTRATION_QUEUE_NAME,
            table_name=SC_REGISTRATION_TABLE_NAME,
        )

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user.name} {self.user.id}")

    async def on_message(self, message):
        if self.user.id != message.author.id:
            if "!register" in message.content:
                # TODO: send discord_id to sqs
                await self.register_user_for_sourcecred(message)

    async def register_user_for_sourcecred(self, message: discord.Message):

        if self._user_already_registered_sourcecred(str(message.author.id)):
            self.logger.info("User already registered for SourceCred. Sending message.")
            message_to_user = (
                "You have already registered for SourceCred. You should be included in the "
                "current cred scores. If you believe you are not, reach out to an admin. Thanks!"
            )
            await self.send_user_dm(message.author.id, message_to_user)

        else:
            registration_fields = self._get_sourcecred_registration_fields(message)
            github = registration_fields.get("github")
            discourse = registration_fields.get("discourse")
            wallet_addr = registration_fields.get("wallet_address")

            embed = discord.Embed(
                title="**Sourcecred registration received**",
                description=f"Received registration request for user {message.author.display_name}. "
                f"Registering user with the following fields.",
            )

            embed.add_field(
                name="Github", value=f"{github}", inline=False
            ) if github else None
            embed.add_field(
                name="Discourse", value=f"{discourse}", inline=False
            ) if discourse else None
            embed.add_field(
                name="Address", value=f"{wallet_addr}", inline=False
            ) if wallet_addr else None

            self.logger.info(f"registration fields: {registration_fields}")
            await self._send_user_registration_to_sqs(registration_fields)
            await message.channel.send(embed=embed)

    def _get_sourcecred_registration_fields(self, message: discord.Message) -> dict:
        registration_fields = {}

        for line in message.content.split("\n"):
            if "github:" in line:
                registration_fields["github"] = line.split(":")[-1].strip()
            elif "discourse:" in line:
                registration_fields["discourse"] = line.split(":")[-1].strip()
            elif "address:" in line:
                registration_fields["wallet_address"] = line.split(":")[-1].strip()

        registration_fields["discord_id"] = message.author.id
        registration_fields["discord_name"] = message.author.display_name

        return registration_fields

    async def _send_user_registration_to_sqs(self, registration_fields: dict):
        sent_message = self._send_sqs_message(self.sc.queue_name, registration_fields)

        if sent_message:
            self.logger.info(f"Successfully sent registration message: {sent_message}")
        else:
            self.logger.error("Error submitting registration message.")
            message_to_user = (
                "There was an issue submitting your SourceCred registration. "
                "Please reach out to an admin or try again later."
            )
            await self.send_user_dm(
                registration_fields.get("discord_id"), message_to_user
            )

    def _send_sqs_message(self, queue_name: str, message: dict):
        sqs_client = boto3.client("sqs")
        sqs_queue_url = sqs_client.get_queue_url(QueueName=queue_name)["QueueUrl"]

        try:
            msg = sqs_client.send_message(
                QueueUrl=sqs_queue_url, MessageBody=json.dumps(message)
            )
        except Exception as e:
            self.logger.error("Error sending SQS message")
            self.logger.error(e)
            return None

        return msg

    async def send_user_dm(self, user_id: str, message: str):
        user = await self.get_user_info(user_id)
        try:
            # dm user letting them know registration failed
            await self.send_message(user, message)
        except:
            self.logger.error("Error sending dm to user.")

    def _user_already_registered_sourcecred(self, user_id: str) -> bool:
        return self.exists_in_dynamodb("discord_id", user_id, self.sc.table_name)

    def exists_in_dynamodb(
        self, key_name: str, key_value: str, table_name: str
    ) -> bool:

        try:
            dynamodb = boto3.resource("dynamodb")
            table = dynamodb.Table(table_name)

            item = table.get_item(Key={key_name: key_value})
        except Exception as e:
            self.logger.error(
                (
                    f"Something went wrong with DynamoDB. "
                    f"Input params were key_name: {key_name}, "
                    f"key_value: {key_value}, table_name: {table_name}."
                )
            )
            self.logger.error(e)
            raise e

        return item.get("Item") != None
