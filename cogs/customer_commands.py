import io
import json
import math
import random
import sqlite3
from typing import Union

import discord
import modules.functions as functions
from discord.ext import commands

from datetime import datetime


def hunter_role():
    with open("db/config.json") as fp:
        config = json.load(fp)
    return config["hunter_role"]

def high_volume_customer():
    with open("db/config.json") as fp:
        config = json.load(fp)
    return discord.utils.get(ctx.guild.roles, id = config["high_volume_customer"] )


priorities = ["normal", "high"]



class Customer(commands.Cog):
    """Customer Commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="order")
    async def _order(self, ctx, item, amount: Union[int, str], priority:str, storage = None):
        """- Place a new order"""

        con = sqlite3.connect("db/orders.db", timeout=10)
        cur = con.cursor()

        with open("db/config.json") as fp:
            config = json.load(fp)

        cur.execute("SELECT count(*) FROM orders WHERE customer LIKE {} AND status IN ('pending', 'in progress')".format(ctx.author.id))
        orders = cur.fetchone()[0]

        with open("./db/config.json") as fp:
            config = json.load(fp)
            high_volume_customer=discord.utils.get(ctx.guild.roles, id = config["customerRoles"]["high_volume_customer"])
            customer_role=discord.utils.get(ctx.guild.roles, id = config["customerRoles"]["customer"])

            if high_volume_customer in ctx.author.roles:
                limit = config["limits"]["high_volume_customer"]
            elif customer_role in ctx.author.roles:
                limit = config["limits"]["customer"]
            else:
                await ctx.reply("You must have either the customer or VIP Customer role to place orders")
                return

        if orders >= limit:
            await ctx.reply(embed=functions.embed_generator(self.bot, "You have reached the maximum amount of orders of {}".format(limit), colour=0x23272A))
            con.close()
            return

        with open("db/config.json") as fp:
            config = json.load(fp)

        with open('db/items.json') as fp:
            items = json.load(fp)

        if not items.get(item.lower()):
            await ctx.reply(embed=functions.embed_generator(self.bot, f"**{item}** is not a valid item.", 0x23272A))
            return

        if amount == "max":
            amount = items[item]["limit"]
        elif amount < 1 :
            await ctx.reply(embed=functions.embed_generator(self.bot, f"The amount must be less or equal to **{limit}**", 0x23272A))
            return

        if priority.lower() not in priorities:
            await ctx.reply(embed=functions.embed_generator(self.bot, "The priority must be either High or Normal", 0x23272A))
            return

        item = item.lower()
        priority = priorities.index(priority.lower())

        cost = items[item]["cost"]
        limit = items[item]["limit"]

        if amount > limit:
            await ctx.reply(embed=functions.embed_generator(self.bot, f"The amount must be less or equal to **{limit}**", 0x23272A))
            return

        cur.execute("SELECT count(*) FROM orders")
        order_id = cur.fetchone()[0] + 1

        cur.execute("SELECT sum(amount) FROM orders WHERE customer LIKE {} AND status IN ('pending', 'in progress')".format(ctx.author.id))
        current_amount = cur.fetchone()[0]
        if not current_amount:
            current_amount=0


        final_cost = cost * amount

        if priority:
            final_cost = round(final_cost * 1.15)

        [discount_id, discount_amount] = functions.discount_active()

        discount_text = ""
        if discount_id:
            final_cost = functions.discount_price(final_cost)
            discount_text = "\n**Discount**: {}%".format(discount_amount)

        final_cost = int(round(final_cost))

        oType = items[item]["type"]

        formatted_cost = "$" + format(final_cost, ",")
        name = (ctx.author.nick or ctx.author.name) + "#" + ctx.author.discriminator
        embed = discord.Embed(title="{} Order Placed - #{}".format(oType, order_id), description="**Customer: **{} ({})\n**Item: **{}\n**Amount: **{}\n**Cost: **{}{}\n**Storage: **{}".format(ctx.author.mention, name, item, amount, formatted_cost, discount_text, storage))

        channel_id = config["orders_channel"]
        channel_log_id = config["orders_log_channel"]
        channel = await self.bot.fetch_channel(channel_id)
        channel_log = await self.bot.fetch_channel(channel_log_id)

        if priority:
            embed.color = 0x8240AF
            message = await channel.send("A priority order has been placed", embed=embed)
            await channel_log.send(embed=embed)
        else:
            embed.color = 0x23272A
            message = await channel.send("A new order has been placed", embed=embed)
            await channel_log.send(embed=embed)


        cur.execute(f"""INSERT INTO orders
                        (order_id, customer, product, amount, storage, cost, messageid, progress, status, priority, discount_id, order_timestamp)
                    VALUES ({order_id}, {ctx.author.id}, ?, ?, ?, {final_cost}, {message.id}, 0,'pending', ?, ?)""", (item.lower(), amount, storage, priority, discount_id, datetime.now()))

        con.commit()
        con.close()

        if discount_id:
            await ctx.send(embed=functions.embed_generator(self.bot, "Thank you for placing your order with United Tycoon, your order number is **#{}**\nThe cost is {} - A discount of {}% is applied".format(order_id, formatted_cost, discount_amount)))
        else:
            await ctx.send(embed=functions.embed_generator(self.bot, "Thank you for placing your order with United Tycoon, your order number is **#{}**\nThe cost is {}".format(order_id, formatted_cost)))


    @commands.command(name="orders")
    async def _orders(self, ctx, user: Union[discord.Member, int] = None):
        """- View your orders"""

        if user is None:
            user = ctx.author
        elif isinstance(user, int):
            user = await self.bot.fetch_user(user)

        con = sqlite3.connect('db/orders.db')
        cur = con.cursor()
        oginfo = f"""SELECT order_id, product, amount, cost, progress, grinder, status, storage, priority, discount_id FROM orders WHERE customer LIKE {user.id} and status not LIKE 'cancelled' and status not LIKE 'delivered' """
        info = cur.execute(oginfo)
        userorders = info.fetchall()

        if userorders == []:
            await ctx.reply(embed=functions.embed_generator(self.bot, "Hey, you don't currently have any orders open with us! head to #Order-Here and place a new one!", colour=0x23272A))
            return

        embed = functions.embed_generator(self.bot, "Here are your current orders:", colour=0xaaFF00, author=user.name, avatar_url=user.avatar_url)
        hasPriority = 0
        for i, x in enumerate(userorders, 1):
            grinderperson = f"<@{str(x[5])}>"
            priority = ""
            discount_text = ""

            if x[5] is None:
                grinderperson = "Not Claimed"

            if x[8]:
                hasPriority = 1
                priority = "**Priority**: High\n"

            if x[9]:
                discount_amount = functions.discount_get_amount(x[9])
                discount_text = "\n**Discount**: {}%".format(discount_amount)

            formatedPrice = "${:,}".format(x[3])
            embed.add_field(name=str(x[1]).title(), value=f"**Order ID**: {str(x[0])}\n{priority}**Product**: {str(x[1])}\n**Amount**: {str(x[2])}\n**Cost**: {formatedPrice}\n**Status**: {str(x[6]).title()}\n**Grinder**: {grinderperson}\n**Progress**: {str(x[4])}/{str(x[2])}{discount_text}", inline=True)

        if hasPriority:
            embed.colour = 0x8240AF

        await ctx.reply(embed=embed)

    @commands.command(name="track")
    async def _track(self, ctx, order_id: int):
        """- Track an order"""
        con = sqlite3.connect('db/orders.db')
        con.row_factory = functions.dict_factory
        cur = con.cursor()

        cur.execute("SELECT * FROM orders WHERE order_id LIKE ?", (order_id,))
        order = cur.fetchone()
        con.close()

        if not order:
            await ctx.reply(embed=functions.embed_generator(self.bot, "Order not found", colour=0x23272A))
            return

        name = ""
        priority = ""
        discount_text = ""

        if not order["grinder"]:
            name = "Unassigned"
        else:
            try:
                grinder = await self.bot.fetch_user(order["grinder"])
                name = grinder.display_name
            except commands.UserNotFound:
                name = "Unknown"

        if order["priority"]:
            priority = "**Priority**: High\n"

        if order["discount_id"]:
            discount_amount = functions.discount_get_amount(order["discount_id"])
            discount_text = "\n**Discount**: {}%".format(discount_amount)

        customer = await self.bot.fetch_user(order["customer"])
        progress = f'{order["progress"]}/{order["amount"]}' + " ({}%)".format(round((order["progress"] / order["amount"]) * 100))
        embed = functions.embed_generator(
                self.bot,
                "**Order ID: **{}\n**Customer: **{}\n{}**Product: **{}\n**Cost: **{}{}\n**Status: **{}\n**Grinder: **{}\n**Progress: **{}".format(
                    order_id,
                    customer.display_name,
                    priority,
                    order["product"],
                    "$" + format(order["cost"], ","),
                    discount_text,
                    order["status"].capitalize(),
                    name,
                    progress,
                ), colour=0x00FF00, author=customer.display_name, avatar_url=customer.avatar_url
            )

        if order["priority"]:
            embed.color = 0x23272A

        await ctx.reply(embed=embed)

    @commands.command(name="slap")
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def _slap(self, ctx, user: discord.Member):
        await ctx.send(f"{ctx.author.mention} delivers an almighty backhand to the face of {user.mention}! <:plp:949282527170949132>")

    #Errors
    @_order.error
    async def order_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.reply(embed=functions.embed_generator(self.bot, "The amount must be a whole number", 0x23272A))
            return

    @_track.error
    async def track_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.reply(embed=functions.embed_generator(self.bot, "The order ID must be a whole number", 0x23272A))
            return



def setup(bot):
    bot.add_cog(Customer(bot))
