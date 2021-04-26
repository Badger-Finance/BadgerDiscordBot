import asyncio
from dotenv import load_dotenv
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from honey_badger import BadgerBot

load_dotenv()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    general_bot_client = BadgerBot(
        github_pat=os.getenv("BADGER_SOURCECRED_PAT_PROD"),
        github_repo="btcookies/SourceCred",
    )
    loop.create_task(general_bot_client.start(os.getenv("BOT_TOKEN_GENERAL")))

    loop.run_forever()
