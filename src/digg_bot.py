import discord
from discord.ext import tasks
from price_bot import PriceBot
import requests
import json
from web3 import Web3

UPDATE_INTERVAL_SECONDS = 45


class DiggBot(PriceBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._get_token_data()

    @tasks.loop(seconds=UPDATE_INTERVAL_SECONDS)
    async def update_price(self):
        """
        Asynchronous function that runs every UPDATE_INTERVAL_SECONDS to get the current price and market of the
        token and update the bot's name and activity in the guild.
        """
        # first get latest token data
        self._get_token_data()

        activity_string = (
            "mcap=$"
            + self._get_number_label(self.token_data.get("market_cap"))
            + " btc="
            + str(round(self.token_data.get("token_price_btc"), 2))
        )
        activity = discord.Activity(
            name=activity_string, type=discord.ActivityType.playing,
        )
        await self.change_presence(activity=activity)
        for guild in self.guilds:
            print(guild.members)
            for member in guild.members:
                if str(member.id) == self.discord_id:
                    await member.edit(
                        nick=f"{self.token_display} $"
                        + str(self.token_data.get("token_price_usd"))
                    )

    @update_price.before_loop
    async def before_update_price(self):
        await self.wait_until_ready()  # wait until the bot logs in