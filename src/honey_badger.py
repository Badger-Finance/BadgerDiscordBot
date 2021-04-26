import discord
from discord.ext import commands, tasks
import json
import math
import os
import requests
from sourcecred import SourceCredManager


class BadgerBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.discord_id = kwargs.get("discord_id")
        self.sc = SourceCredManager(kwargs.get("github_pat"), kwargs.get("github_repo"))

    async def on_ready(self):
        print("Logged in as")
        print(self.user.name)
        print(self.user.id)
        print("------")

    async def on_message(self, message):
        if self.user.id != message.author.id:
            if "!register" in message.content:
                # TODO: send discord_id to sqs
                await self.register_user_for_sourcecred(message)
                pass

    async def register_user_for_sourcecred(self, message: discord.Message):
        print(message.author.id)
        registration_fields = self._get_sourcecred_registration_fields(message)
        github = registration_fields.get("github")
        discourse = registration_fields.get("discourse")
        wallet_addr = registration_fields.get("wallet_address")
        # self.sc.activate_discord_users([message.author.id])
        embed = discord.Embed(
            title="**Sourcecred registration received**",
            description=f"Received registration request for user {message.author.display_name}. "
            f"Please validate the following fields are correct and react with :thumbsup:.",
        )
        embed.add_field(name="Github", value=f"{github}", inline=False)
        embed.add_field(name="Discourse", value=f"{discourse}", inline=False)
        embed.add_field(name="Address", value=f"{wallet_addr}", inline=False)

        print(f"registration fields: {registration_fields}")

        await message.channel.send(embed=embed)

    def _get_sourcecred_registration_fields(self, message: discord.Message):
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
