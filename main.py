import json
import os

import discord
from discord.ext import commands


from dotenv import load_dotenv

load_dotenv()
token = os.getenv('DISCORD_TOKEN')


with open('db/config.json') as fp:
    config = json.load(fp)

bot = commands.Bot(command_prefix=config["bot_prefix"], help_command=None, intents=discord.Intents.default())

@bot.event
async def on_ready():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            bot.load_extension(f"cogs.{filename[:-3]}")

    # Load each slash command


    if(os.getenv('ENV') == 'DEV'):
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"code"))
    else:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"{config['bot_prefix']}help"))
    print('Ready!')

bot.run(token)