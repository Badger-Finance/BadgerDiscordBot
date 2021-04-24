import discord
from discord.ext import commands, tasks
import json
import math
import os
import requests

UPDATE_INTERVAL_SECONDS = 45


class PriceBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.token_ticker = kwargs.get("token_ticker")
        self.token_symbol = kwargs.get("token_symbol")
        self.discord_id = kwargs.get("discord_id")
        self._get_token_data()

        self.update_price.start()

    async def on_ready(self):
        print("Logged in as")
        print(self.user.name)
        print(self.user.id)
        print("------")

    @tasks.loop(seconds=UPDATE_INTERVAL_SECONDS)
    async def update_price(self):
        """
        Asynchronous function that runs every UPDATE_INTERVAL_SECONDS to get the current price and market of the 
        token and update the bot's name and activity in the guild.
        """
        self._get_token_data()
        activity = discord.Activity(
            name="marketcap=$"
            + self._get_number_label(self.token_data.get("market_cap")),
            type=discord.ActivityType.playing,
        )
        await self.change_presence(activity=activity)
        for guild in self.guilds:
            print(guild.members)
            for member in guild.members:
                if str(member.id) == self.discord_id:
                    await member.edit(nick=f"{self.token_symbol} $" + str(self.token_data.get("token_price")))

    @update_price.before_loop
    async def before_update_price(self):
        await self.wait_until_ready()  # wait until the bot logs in

    def _get_token_data(self):
        """
        Private function to make call to coingecko to retrieve price and market cap for the token and update 
        token data property.
        """
        response = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{self.token_ticker}"
        ).content
        token_data = json.loads(response)

        token_price = token_data.get("market_data").get("current_price").get("usd")
        market_cap = token_data.get("market_data").get("market_cap").get("usd")

        self.token_data = {"token_price": token_price, "market_cap": market_cap}

    def _get_number_label(self, value: str) -> str:
        """
        Formats number in billions, millions, or thousands into Discord name friendly string

        Args:
            value (str): value between 0 - 999 billion

        Returns:
            str: formatted string. EG if 1,000,000,000 is passed in, will return 1B
        """
        # Nine Zeroes for Billions
        if abs(int(value)) >= 1.0e9:
            return str(round(abs(int(value)) / 1.0e9)) + "B"
        # Six Zeroes for Millions
        elif abs(int(value)) >= 1.0e6:
            return str(round(abs(int(value)) / 1.0e6)) + "M"
        # Three Zeroes for Thousands
        elif abs(int(value)) >= 1.0e3:
            return str(round(abs(int(value)) / 1.0e3)) + "K"
        else:
            return str(abs(int(value)))

