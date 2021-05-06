from decimal import Decimal
import discord
from discord.ext import tasks
from dotenv import load_dotenv
from price_bot import PriceBot
import os
import requests
import json
from time import sleep
from web3 import Web3

load_dotenv()

UPDATE_INTERVAL_SECONDS = 45

UNISWAP_SUBGRAPH = os.getenv("UNISWAP_SUBGRAPH")
WBTC_USDC_PAIR_ID = os.getenv("WBTC_USDC_PAIR_ID")
UNISWAP_POOL_QUERY = """
    query($pairId: String!) {
        pair(
            id: $pairId
        ) {
            id
            liquidityProviderCount
            reserveUSD
            token0 {
                name
            }
            token0Price
            token1 {
                name
            }
            token1Price
            volumeToken0
            volumeToken1
            volumeUSD
        }
    }
    """


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
            name=activity_string,
            type=discord.ActivityType.playing,
        )
        await self.change_presence(activity=activity)
        for guild in self.guilds:
            self.logger.info(guild.members)
            for member in guild.members:
                if str(member.id) == self.discord_id:
                    try:
                        await member.edit(
                            nick=f"{self.token_display} $"
                            + str(round(self.token_data.get("token_price_usd")))
                        )
                    except Exception as e:
                        self.logger.error("Error updated nickname")
                        self.logger.error(e)
                        webhook = discord.Webhook.from_url(os.getenv("DISCORD_MONITORING_WEBHOOK_URL"), adapter=discord.RequestsWebhookAdapter())
                        embed = discord.Embed(
                            title=f"**{self.token_display} Price Bot Error**",
                            description=f"Error message: {e}"
                        )
                        webhook.send(embed=embed, username="Price Bot Monitoring")

    @update_price.before_loop
    async def before_update_price(self):
        await self.wait_until_ready()  # wait until the bot logs in

    def _get_token_data(self):
        """
        Private function to make call to thegraph to retrieve price and market cap for the token and update
        token data property.
        """
        response = self.session.get(
            f"https://api.coingecko.com/api/v3/coins/{self.coingecko_token_id}"
        ).content
        token_data = json.loads(response)

        token_price_btc = self._get_digg_wbtc_price()
        token_price_usd = token_price_btc * self._get_wbtc_usdc_price()
        market_cap = token_price_usd * Decimal(self._get_supply())

        self.token_data = {
            "token_price_usd": token_price_usd,
            "token_price_btc": token_price_btc,
            "market_cap": market_cap,
        }

    def _get_digg_wbtc_price(self, retry: bool = False):
        #TODO: use chainlink oracle to do this
        if retry:
            sleep(2)

        variables = {"pairId": os.getenv("WBTC_DIGG_PAIR_ID")}

        request = self.session.post(
            UNISWAP_SUBGRAPH,
            json={"query": UNISWAP_POOL_QUERY, "variables": variables},
        )
        try:
            self.logger.info(f"digg_wbtc_price: {request.json()}")
        except json.decoder.JSONDecodeError as e:
            self.logger.error(f"Error getting json {e}")
            self._get_digg_wbtc_price(retry=True)

        return (
            self._get_digg_wbtc_price(retry=True)
            if request.json().get("data", {}).get("pair") == None
            else Decimal(request.json().get("data").get("pair").get("token0Price"))
        )

    def _get_wbtc_usdc_price(self) -> Decimal:

        variables = {"pairId": WBTC_USDC_PAIR_ID}

        request = self.session.post(
            UNISWAP_SUBGRAPH,
            json={"query": UNISWAP_POOL_QUERY, "variables": variables},
        )

        self.logger.info(f"wbtc_usdc_price: {request.json()}")

        return Decimal(request.json()["data"]["pair"]["token1Price"])

    def _get_supply(self):
        supply = (
            self.token_contract.functions.totalSupply().call()
            / 10 ** self.token_contract.functions.decimals().call()
        )
        return supply
