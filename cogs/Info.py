import json

import discord
from discord.ext import commands

from datetime import datetime
import modules.functions as functions


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command(name="items")
    @commands.has_permissions(administrator=True)
    async def _items(self, ctx):
        with open('db/items.json') as fp:
            items = json.load(fp)

        itemsText = ""
        itemType = items[list(items.keys())[0]]['type']
        columnLength = 20

        embed = discord.Embed()

        for item in items:
            if itemType != items[item]['type']:
                separator = len(max(itemsText.split('\n'), key=len))
                itemsText = f"```css\nItem:               Cost:         (Cost 15%):         Limit:\n{'-'*separator}\n{itemsText}```"
                embed.add_field(name=itemType + ":", value=itemsText, inline=False)
                itemType = items[item]['type']
                itemsText = ""

            itemCost = f"{items[item]['cost']:,}"
            highItemCost = f"{items[item]['cost'] * 1.15:,}"

            itemsText += f"{item.title()}{' '*(columnLength-len(item))}${itemCost}{' '*(columnLength-len(itemCost)-7)}(${highItemCost}{' '*(columnLength-len(highItemCost)-7)}){items[item]['limit']:,}\n\n"

            if itemType == "Kits":
                # Remove '\n' from the end of the itemsTex
                itemsText = itemsText[:-1] + "|\n|               (Includes):\n"


                for incItem in items[item]['includes']:

                    line = "|"
                    # If the item is the last key in the object, add a pipe to the end
                    if incItem == list(items[item]['includes'].keys())[-1]:
                        line = "\\"

                    itemsText += f"{line}-->{' '*(columnLength-4)}{incItem}{' '*(columnLength-len(incItem)-6)}{items[item]['includes'][incItem]:,}\n"

                    if incItem == list(items[item]['includes'].keys())[-1]:
                        itemsText += "\n"

            if len(itemsText) + ((len(item) + columnLength)*3) + 100 >= 1024:
                itemType = items[item]['type']
                #Calculate the longest line in the message and set the separator to that length
                separator = len(max(itemsText.split('\n'), key=len))
                itemsText = f"```css\nItem:               Cost:         (Cost 15%):         Limit:\n{'-'*separator}\n{itemsText}```"
                embed.add_field(name=itemType + ":", value=itemsText, inline=False)
                itemsText = ""

        if itemsText != "":
            itemsText = f"```css\nItem:               Cost:         (Cost 15%):         Limit:\n{'-'*separator}\n{itemsText}```"
            embed.add_field(name=itemType + ":", value=itemsText, inline=False)

        embed.color = 0xffbb00
        # Last updated is the current date and time
        embed.set_footer(text=f"Last updated: {datetime.now().strftime('%Y-%m-%d')}")
        await ctx.send(embed=embed)

    @commands.command(name="help")
    async def _help(self, ctx):
        await ctx.reply(embed=functions.embed_generator(self.bot, f"{ctx.author.mention}\n This is a list of our commands\n \n __**Customer Commands:**__ \n**>order**: This command allows you to place an order in #order-here\n *>order [item] [amount] [priority] [storage]* \n \n **>track**: This command allows you to track your order in #order-progress\n *>track [order number]* \n \n __**Grinder Commands**__: \n **>claim**: This command allows grinders to claim an order.\n *>claim [order number]*\n\n **>progress**: This command allows you to update the progress on an order. \n *>progress [order number] [amount]* \n\n **>stats**: This allows both customers and grinders to see their stats in the server. \n *>stats (optional: @username to see another users stats)* \n\n **>delivered**: This command allows you to mark an order as delivered once the customer has receieved it. \n *>delivered [order number]* \n \n **>unclaim**: This command allows a grinder to unclaim an order. Please use this only with a manager's permission. \n *>unclaim [order number]*\n \n __**Manager Commands**__ \n **>cancel**: This command allows an admin or manager to cancel an order with a valid reason. \n *>cancel [order number]* \n\n **>update**: This command allows admins to update order amounts. \n *>update [order number] amount* \n\n **>updatestorage**: This command allows admins to update storages. \n *>update [order number] storage*", colour=0x23272A))
        return


def setup(bot):
    bot.add_cog(Info(bot))
