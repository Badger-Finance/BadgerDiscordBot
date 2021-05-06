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

logging.basicConfig(
    # filename="price_bots_log.txt",
    # filemode='a',
    # format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    # datefmt='%H:%M:%S',
    level=logging.INFO
)

SC_REGISTRATION_TABLE_NAME = os.getenv("SC_REGISTRATION_TABLE_NAME")
SC_REGISTRATION_QUEUE_NAME = os.getenv("SC_REGISTRATION_QUEUE_NAME")
REGISTER_POLL_INTERVAL_HOURS = 1


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
        # aws resources for storing data
        self.sqs_client = boto3.client("sqs")
        self.sourcecred_queue_url = self.sqs_client.get_queue_url(
            QueueName=SC_REGISTRATION_QUEUE_NAME
        )["QueueUrl"]
        self.sourcecred_queue = boto3.resource("sqs").get_queue_by_name(
            QueueName=SC_REGISTRATION_QUEUE_NAME
        )

        self.dynamodb_resource = boto3.resource("dynamodb")
        self.registration_table = self.dynamodb_resource.Table(
            SC_REGISTRATION_TABLE_NAME
        )

        self.process_outstanding_registration_requests.start()

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user.name} {self.user.id}")

    async def on_message(self, message):
        if self.user.id != message.author.id:
            if message.content.startswith("!register"):
                await self.submit_sourcecred_user_registration(message)
            elif message.content.startswith("!kudos"):
                await self.submit_sourcecred_user_registration(message)
            elif message.content.startswith("!mention"):
                await self.mention_user(message)
    @tasks.loop(minutes=REGISTER_POLL_INTERVAL_HOURS)
    async def process_outstanding_registration_requests(self):
        """
        Asynchronous function that runs every REGISTER_POLL_INTERVAL_HOURS to get all of the
        current sourcecred registration requests and invoke the SourceCredManager to register
        the users to the ledger.json
        """
        self.logger.info("Checking for outstanding registration requests.")
        # poll queue to get messages
        registration_messages = self._get_outstanding_registration_messages()

        # check and make sure not duplicate messages from user, if so only process latest one
        unique_registrations = self._get_unique_registrations(registration_messages)

        self.logger.info(f"unique registrations received: {unique_registrations}")

        # submit list of discord ids to register on sourcecred
        discord_ids = [discord_id for discord_id in unique_registrations.keys()]
        self.logger.info(f"submitting discord_ids {discord_ids}")

        activated_users = self.sc.activate_discord_users(discord_ids)

        # after successful registration, add entry to db for user marking them registered
        if len(activated_users) > 0:
            self._mark_users_activated(activated_users, unique_registrations)
            self.logger.info("Successfully activated following users")
            self.logger.info(activated_users)

    @process_outstanding_registration_requests.before_loop
    async def before_update_price(self):
        await self.wait_until_ready()  # wait until the bot logs in

    async def submit_sourcecred_user_registration(self, message: discord.Message):
        self.logger.info("Received sourcecred user registration message.")

        if self._user_already_registered_sourcecred(str(message.author.id)):
            self.logger.info("User already registered for SourceCred. Sending message.")
            message_to_user = (
                "You have already registered for SourceCred. You should be included in the "
                "current cred scores. If you believe you are not, reach out to an admin. Thanks!"
            )
            await self.send_user_dm(int(message.author.id), message_to_user)

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
                name="Discord", value=f"{message.author.display_name}", inline=False
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
            if line.startswith("github:"):
                registration_fields["github"] = line.split(":")[-1].strip()
            elif line.startswith("discourse:"):
                registration_fields["discourse"] = line.split(":")[-1].strip()
            elif line.startswith("address:"):
                registration_fields["wallet_address"] = line.split(":")[-1].strip()

        registration_fields["discord_id"] = str(message.author.id)
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
                int(registration_fields.get("discord_id")), message_to_user
            )

    def _send_sqs_message(self, queue_name: str, message: dict):

        try:
            msg = self.sqs_client.send_message(
                QueueUrl=self.sourcecred_queue_url, MessageBody=json.dumps(message)
            )
        except Exception as e:
            self.logger.error("Error sending SQS message")
            self.logger.error(e)
            return None

        return msg

    async def send_user_dm(self, user_id: int, message: str):
        try:
            # dm user letting them know registration failed
            user = await self.fetch_user(user_id)
            await user.send(message)
        except Exception as e:
            self.logger.error("Error sending dm to user.")
            self.logger.error(e)

    def _user_already_registered_sourcecred(self, user_id: str) -> bool:
        return self.exists_in_dynamodb("discord_id", user_id, self.sc.table_name)

    def exists_in_dynamodb(
        self, key_name: str, key_value: str, table_name: str
    ) -> bool:

        try:
            table = self.dynamodb_resource.Table(table_name)
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

    def _get_outstanding_registration_messages(self) -> list:

        all_messages = []
        current_batch = self.sourcecred_queue.receive_messages()

        while len(current_batch) > 0:
            all_messages.extend(current_batch)
            current_batch = self.sourcecred_queue.receive_messages()

        return all_messages

    def _get_unique_registrations(self, registration_messages: list) -> dict:
        """
        Takes list of sourcecred registration mesages from sqs and returns
        a dict containing the unique ones

        Args:
            registration_messages (list): list of raw sqs messages from sourcecred
            registration queue

        Returns:
            dict: example struct
            {
                "discord_id_1": {
                    "discord_name": "ExampleUser#0001"
                },
                "discord_id_2": {
                    "discord_name": "ExampleUser#0002",
                    "github": "ExampleUser",
                    "discourse": "ExampleUser",
                    "wallet_address": "0x1234567890123456789"
                },
            }
        """
        unique_registrations = {}

        for message in registration_messages:
            if message.body:
                body = json.loads(message.body)
                discord_id = body.get("discord_id")
                if discord_id == None:
                    self.logger.error(f"Discord id is null for message {body}")
                else:
                    unique_registrations[discord_id] = body
                    self.logger.info(
                        (f"Processed message for user {discord_id} with body {body}")
                    )
            else:
                self.logger.info(f"No body for message {message}")
            # Let the queue know that the message is processed
            message.delete()

        return unique_registrations

    def _mark_users_activated(self, activated_users: list, unique_registrations: dict):
        for user_id in activated_users:
            user_data = unique_registrations.get(user_id)
            if user_data:
                self.add_user_to_dynamodb(user_data)
            else:
                self.logger.error(
                    f"Something wrong, activated user {user_id} not exist in unique registrations"
                )

    def add_user_to_dynamodb(self, data):
        self.registration_table.update_item(
            Key={"discord_id": data.get("discord_id")},
            ExpressionAttributeNames={
                "#G": "github_username",
                "#DS": "discourse_username",
                "#W": "wallet_address",
                "#DD": "discord_username",
            },
            ExpressionAttributeValues={
                ":g": data.get("github"),
                ":ds": data.get("discourse"),
                ":w": data.get("wallet_address"),
                ":dd": data.get("discord_name"),
            },
            UpdateExpression="SET #G=:g, #DS=:ds, #W=:w, #DD=:dd",
        )
        self.logger.info(f"Registered user with data {data}")
    
    async def mention_user(self, message: discord.Message):
        message_to_user = f"Test mention <@{str(message.author.id)}>"
        await self.send_user_dm(int(message.author.id), message_to_user)

