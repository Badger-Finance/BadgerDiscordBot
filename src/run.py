import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import json
import os
import requests
from sourcecred import SourceCred

load_dotenv()

BADGER_PRICE_BOT_TOKEN = os.getenv("BOT_TOKEN_BADGER")

client = discord.Client()


@client.event
async def on_ready():
    print(f"{client.user} has connected to Discord!")


if __name__ == "__main__":
    client.run(BADGER_PRICE_BOT_TOKEN)
