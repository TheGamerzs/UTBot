import json

import discord
import modules.functions as functions
from discord.ext import commands


def error_channel():
    with open('db/config.json') as fp:
        config = json.load(fp)
    return config["error_log_channel"]

class errors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            pass
        elif isinstance(error, (commands.MissingAnyRole, commands.MissingPermissions)):
            await ctx.reply(embed=functions.embed_generator(self.bot, "You are missing the permissions required to run this command", colour=0x23272A))

        elif isinstance(error, commands.MissingRequiredArgument):
            # send error reply including the error message and capitialize the first letter of the argument name
            await ctx.reply(embed=functions.embed_generator(self.bot, f"Missing required argument: {error.param.name.replace('_', ' ').title()}", colour=0x23272A))

        else:
            # send to error log channel including line number
            await self.bot.get_channel(error_channel()).send(embed=functions.embed_generator(self.bot, f"{ctx.author.mention} ran the command `{ctx.command}` and got the error `{error}`", colour=0xff0000))

def setup(bot):
    bot.add_cog(errors(bot))
