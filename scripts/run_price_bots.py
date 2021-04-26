import asyncio
from dotenv import load_dotenv
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from honey_badger import BadgerBot
from price_bot import PriceBot

load_dotenv()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    digg_client = PriceBot(
        coingecko_token_id="digg",
        token_display="DIGG",
        discord_id=os.getenv("BOT_ID_DIGG"),
    )
    bdigg_client = PriceBot(
        coingecko_token_id="badger-sett-digg",
        token_display="bDIGG",
        token_address=os.getenv("BDIGG_ADDRESS"),
        token_abi=os.getenv("BDIGG_ABI"),
        discord_id=os.getenv("BOT_ID_BDIGG"),
    )
    badger_client = PriceBot(
        coingecko_token_id="badger-dao",
        token_display="BADGER",
        discord_id=os.getenv("BOT_ID_BADGER"),
    )
    bbadger_client = PriceBot(
        coingecko_token_id="badger-sett-badger",
        token_display="bBADGER",
        token_address=os.getenv("BBADGER_ADDRESS"),
        token_abi=os.getenv("BBADGER_ABI"),
        discord_id=os.getenv("BOT_ID_BBADGER"),
    )
    loop.create_task(digg_client.start(os.getenv("BOT_TOKEN_DIGG")))
    loop.create_task(bdigg_client.start(os.getenv("BOT_TOKEN_BDIGG")))
    loop.create_task(badger_client.start(os.getenv("BOT_TOKEN_BADGER")))
    loop.create_task(bbadger_client.start(os.getenv("BOT_TOKEN_BBADGER")))

    loop.run_forever()
