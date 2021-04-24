import asyncio
from dotenv import load_dotenv
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
)

from price_bot import PriceBot

load_dotenv()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    digg_client = PriceBot(token_ticker="digg", token_symbol="DIGG", discord_id=os.getenv("BOT_ID_DIGG"))
    bdigg_client = PriceBot(token_ticker="badger-sett-digg", token_symbol="BDIGG", discord_id=os.getenv("BOT_ID_BDIGG"))
    badger_client = PriceBot(token_ticker="badger-dao", token_symbol="BADGER", discord_id=os.getenv("BOT_ID_BADGER"))
    bbadger_client = PriceBot(token_ticker="badger-sett-badger", token_symbol="BBADGER", discord_id=os.getenv("BOT_ID_BBADGER"))

    loop.create_task(digg_client.start(os.getenv("BOT_TOKEN_DIGG")))
    loop.create_task(bdigg_client.start(os.getenv("BOT_TOKEN_BDIGG")))
    loop.create_task(badger_client.start(os.getenv("BOT_TOKEN_BADGER")))
    loop.create_task(bbadger_client.start(os.getenv("BOT_TOKEN_BBADGER")))

    loop.run_forever()