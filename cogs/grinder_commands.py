import json
import math
import random
import re
import sqlite3
from distutils import config
from typing import Union

import discord
import modules.functions as functions
from discord.ext import commands

from datetime import datetime

def hunter_role():
    with open("db/config.json") as fp:
        config = json.load(fp)
    return config["hunter_role"]


class Grinder(commands.Cog):
    """Grinder Commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="claim", aliases=["c"])
    @commands.has_any_role(hunter_role())
    async def _claim(self, ctx, order_id: int):
        """- Claim an order"""
        con = sqlite3.connect('db/orders.db')
        con.row_factory = functions.dict_factory
        cur = con.cursor()

        cur.execute("SELECT * FROM orders WHERE order_id LIKE ?", (order_id,))
        order = cur.fetchone()
        if not order:
            await ctx.reply(embed=functions.embed_generator(self.bot, "Order not found", colour=0xff0000))
            con.close()
            return

        if order["status"] == "cancelled":
            await ctx.reply(embed=functions.embed_generator(self.bot, "This order has been cancelled", colour=0xff0000))
            con.close()
            return

        if order["grinder"]:
            await ctx.reply(embed=functions.embed_generator(self.bot, "This order is already assigned.", colour=0x330000))
            con.close()
            return

        with open("db/config.json") as fp:
            config = json.load(fp)


        cur.execute("UPDATE orders SET grinder = ?, status = 'in progress', claim_timestamp = ? WHERE order_id LIKE ?", (ctx.author.id, datetime.now(), order_id))
        con.commit()
        con.close()

        await ctx.reply(embed=functions.embed_generator(self.bot, "You have successfully claimed order #{}".format(order_id), colour=0x00ff55))

        # delete order messageid
        await self.bot.http.delete_message(config["orders_channel"], order["messageid"])

        #Log the claim
        log_channel = self.bot.get_channel(config["log_channel"])
        await log_channel.send(embed=functions.embed_generator(self.bot, "Order #{} has been claimed by {}".format(order_id, ctx.author.mention), colour=0x00ff55))

    @commands.command(name="progress", aliases=["p"])
    @commands.has_any_role(hunter_role())
    async def _progress(self, ctx, order_id: int, progress):
        """- Update an order"""
        if not re.match(r"^[+-]?\d+$", progress):
            await ctx.reply(embed=functions.embed_generator(self.bot, "Progress must be an integer", colour=0xFF0000))
            return

        con = sqlite3.connect('db/orders.db')
        con.row_factory = functions.dict_factory
        cur = con.cursor()
        cur.execute("SELECT * FROM orders WHERE order_id LIKE ?", (order_id,))
        order = cur.fetchone()

        # Check if order exists, author is grinder, order is in progress, progress is not over order amount, progress is not negative

        if not order:
            await ctx.reply(embed=functions.embed_generator(self.bot, "Order not found", colour=0xFF0000))
            con.close()
            return

        if ctx.author.id != order["grinder"]:
            await ctx.reply(embed=functions.embed_generator(self.bot, "This order is not assigned to you", 0xFF0000))
            con.close()
            return

        if order["status"] != "in progress":
            await ctx.reply(embed=functions.embed_generator(self.bot, "The order status is `{}`. The order must be `in progress` to make changes.".format(order["status"]), 0xFF0000))
            con.close()
            return


        if not isinstance(progress, int) and (progress.startswith("+") or progress.startswith("-")):
            operator = progress[0]
            progress = int(progress[1:])
            progress = order["progress"] + progress if operator == "+" else order["progress"] - progress
        else:
            progress = int(progress)


        if progress > order["amount"]:
            await ctx.reply(embed=functions.embed_generator(self.bot, "{} is exceeding the amount required".format(progress), 0xFF0000))
            con.close()
            return

        if progress < 0:
            await ctx.reply(embed=functions.embed_generator(self.bot, "Progress cannot be negative", 0xFF0000))
            con.close()
            return

        with open('db/config.json') as fp:
            config = json.load(fp)
        # Update progress, if

        if progress == order["amount"]:
            collection_channel = await self.bot.fetch_channel(config["collection_channel"])
            try:
                grinder = await self.bot.fetch_user(order["grinder"])
                name = f"{grinder.mention} ({grinder.display_name}#{grinder.discriminator})"
            except:
                name = "Please contact staff"
            await collection_channel.send(f"<@{order['customer']}>", embed=functions.embed_generator(self.bot, "**Order #{} - Ready For Collection**\n**Product: **{}\n**Amount: **{}\n**Cost: **{}\n**Grinder: **{}".format(
                order_id,
                order["product"],
                order["amount"],
                "$" + format(order["cost"], ","),
                name
            ), 0x00FF00))
            cur.execute("UPDATE orders SET progress = amount, status = 'complete' WHERE order_id LIKE ?", (order_id,))
            con.commit()
            con.close()
            await ctx.reply(embed=functions.embed_generator(self.bot, "Successfully updated order #{}.\nThe customer has been notified that their order is complete.".format(order_id), 0x00FF00))

        else:
            cur.execute("UPDATE orders SET progress = ? WHERE order_id LIKE ?", (progress, order_id))
            con.commit()
            con.close()
            await ctx.reply(embed=functions.embed_generator(self.bot, "Successfully updated order #{}.\n**Progress: ** {}/{} ({}%)".format(
                order_id,
                progress,
                order["amount"],
                round((progress/order["amount"]) * 100)
            ), colour=0x00FF00))

        # Log the progress
        log_channel = self.bot.get_channel(config["log_channel"])
        await log_channel.send(embed=functions.embed_generator(self.bot, "Order #{} has been updated to {}/{} ({}%)".format(order_id, progress, order["amount"], round((progress/order["amount"]) * 100)), colour=0x00FF00))

    @commands.command(name="current", aliases=["cur"])
    async def _current(self, ctx, user: Union[discord.Member, int] = None):
        con = sqlite3.connect('db/orders.db')
        cur = con.cursor()

        if user is None:
            user = ctx.author
        elif isinstance(user, int):
            user = await self.bot.fetch_user(user)

        oginfo = f"""SELECT order_id, customer, product, amount , cost , progress , grinder, storage, status FROM orders WHERE grinder LIKE {user.id} and status not LIKE 'cancelled' and status not LIKE 'delivered' """
        info = cur.execute(oginfo)
        userorders = info.fetchall()

        if userorders == []:
            await ctx.reply(embed=functions.embed_generator(self.bot, "Hey, you dont currently have any orders assigned to you!", colour=0x23272A))
            return

        embed = discord.Embed(title=f"{user.display_name}'s Orders! ", colour = 0x23272A)
        for i, x in enumerate(userorders, 1):
            grinderperson = f"<@{str(x[6])}>"
            if grinderperson is None:
                grinderperson = "Not Claimed"

            formatedPrice = "${:,}".format(x[4])
            embed.add_field(name=f"Order #{str(x[0])}", value=f"**Customer**: <@{str(x[1])}>\n**Product**: {str(x[2]).title()}\n**Amount**: {str(x[3])}\n**Cost**: {formatedPrice}\n**Status**: {str(x[8]).title()}\n**Grinder**: {grinderperson}\n**Progress**: {str(x[5])}/{str(x[3])}\n**Storage**: {str(x[7])}", inline=True)
        await ctx.reply(embed=embed)

    @commands.command(name="delivered")
    @commands.has_any_role(hunter_role())
    async def _delivered(self, ctx, order_id: int):
        """- Deliver an order"""
        con = sqlite3.connect('db/orders.db')
        con.row_factory = functions.dict_factory
        cur = con.cursor()
        cur.execute("SELECT * FROM orders WHERE order_id LIKE ?", (order_id,))
        order = cur.fetchone()

        if not order:
            await ctx.reply(embed=functions.embed_generator(self.bot, "Order not found", colour=0x23272A))
            con.close()
            return

        if ctx.author.id != order["grinder"] and ctx.author.id != order["second_grinder"]:
            await ctx.reply(embed=functions.embed_generator(self.bot, "This order is not assigned to you", 0x23272A))
            con.close()
            return

        if order["status"] != "complete":
            await ctx.reply(embed=functions.embed_generator(self.bot, "The order status is `{}`. The order must be `complete` to mark as delivered.".format(order["status"]), 0x23272A))

            con.close()
            return
        with open("db/config.json") as fp:
            config = json.load(fp)


        cur.execute("UPDATE orders SET status = 'delivered' WHERE order_id like ?", (order_id,))
        con.commit()
        con.close()
        await ctx.reply(embed=functions.embed_generator(self.bot, "Successfully delivered order #{}".format(order_id), 0x23272A))

        # Log the delivery
        log_channel = self.bot.get_channel(config["log_channel"])
        await log_channel.send(embed=functions.embed_generator(self.bot, "Order #{} has been marked as delivered".format(order_id), 0x23272A))

    @commands.command(name="unclaim")
    @commands.has_any_role(hunter_role())
    async def _unclaim(self, ctx, order_id:int):
        """- Unclaim an order"""
        con = sqlite3.connect('db/orders.db')
        con.row_factory = functions.dict_factory
        cur = con.cursor()

        with open("db/config.json") as fp:
            config = json.load(fp)

        with open("db/items.json") as fp:
            items = json.load(fp)

        orders_channel = self.bot.get_channel(config["orders_channel"])

        cur.execute("SELECT * FROM orders WHERE order_id LIKE ? AND grinder = ?", (order_id, ctx.author.id))
        order = cur.fetchone()

        if order is None:
            await ctx.send("Order {} not found.".format(order_id))
            return

        cur.execute("UPDATE orders SET grinder = NULL, status = 'pending' WHERE order_id LIKE ?", (order_id,))
        con.commit()

        await ctx.reply(embed=functions.embed_generator(self.bot, "You have unclaimed this order #{}".format(order_id), colour=0x00FF00))

        embed = discord.Embed(title="{} Order Placed - #{}".format(items[order["product"]]["type"], order_id), description="**Customer: **<@{}>\n**Item: **{}\n**Amount: **{}\n**Cost: **{}\n**Storage: **{}".format(order['customer'], order['product'], order['amount'], order['cost'], order['storage']), colour=0x23272A)

        msg = await orders_channel.send(embed=embed)

        # Update the order message with the new order message id
        con.execute("UPDATE orders SET messageid = ? WHERE order_id LIKE ?", (msg.id, order_id))
        con.commit()
        con.close()

        log_channel = self.bot.get_channel(config["log_channel"])

        # Log the unclaim
        embed = discord.Embed(title="Order Unclaimed", description="Grinder: {}\nOrder: {}".format(ctx.author.mention, order_id), colour=0x23272A)
        await log_channel.send(embed=embed)

    @commands.command(name="duo")
    @commands.has_any_role(hunter_role())
    async def _duo(self, ctx, order_id: int):
        """- Claim The Secondary Position On An Order"""
        con = sqlite3.connect('db/orders.db')
        con.row_factory = functions.dict_factory
        cur = con.cursor()

        cur.execute("SELECT * FROM orders WHERE order_id LIKE ?", (order_id,))
        order = cur.fetchone()

        if not order:
            await ctx.reply(embed=functions.embed_generator(self.bot, "Order not found", colour=0x23272A))
            con.close()
            return

        if order["status"] == "cancelled":
            await ctx.reply(embed=functions.embed_generator(self.bot, "This order has been cancelled", colour=0x23272A))
            con.close()
            return

        if order["second_grinder"]:
            await ctx.reply(embed=functions.embed_generator(self.bot, "This order is already assigned.", colour=0x23272A))
            con.close()
            return

        cur.execute("UPDATE orders SET second_grinder = ?, status = 'in progress' WHERE order_id LIKE ?", (ctx.author.id, order_id))
        con.commit()
        con.close()

        await ctx.reply(embed=functions.embed_generator(self.bot, "You have successfully claimed the second grinder position on this order #{}".format(order_id), 0x23272A))

    @commands.command(name="stats")
    async def _stats(self, ctx, user: Union[discord.Member, int] = None):
        """ - User Stats"""
        con = sqlite3.connect('db/orders.db')
        con.row_factory = functions.dict_factory
        cur = con.cursor()

        if user is None:
            user = ctx.author
        elif isinstance(user, int):
            user = await self.bot.fetch_user(user)

        cur.execute("SELECT * FROM orders WHERE customer LIKE ?", (user.id,))
        orders = cur.fetchall()

        cur.execute("SELECT * FROM orders WHERE grinder LIKE ?", (user.id,))
        grinder_orders = cur.fetchall()

        if not orders and not grinder_orders:
            await ctx.reply(embed=functions.embed_generator(self.bot, "No orders found for {}".format(user.display_name), colour=0x23272A))
            return

        total_order = len(orders)
        total_spent = 0
        total_amount_products = 0
        total_overall_progress = 0

        for order in orders:
            total_spent += order["cost"]
            total_amount_products += order["amount"]
            total_overall_progress += order["progress"]

            total_spent = int(total_spent)

        embed = functions.embed_generator(self.bot, f"Hey {ctx.author.mention}!\n These are the stats for {user.mention}".format(user.display_name), colour=0x23272A, author=user.display_name, avatar_url=user.avatar_url)
        embed.add_field(name="\u200b", value="__**Customer Stats**__", inline=False)
        embed.add_field(name="Your Orders", value=total_order, inline=False)
        embed.add_field(name="Amount of Products", value=total_amount_products, inline=False)
        embed.add_field(name="Amount Spent", value="${:,}".format(total_spent), inline=False)

        grinder = [functions.hunter_role(), functions.bxp_role()]

        if any(role.id in grinder for role in user.roles):
            cur.execute("SELECT * FROM orders WHERE grinder LIKE ?", (user.id,))
            orders = cur.fetchall()

            total_claimed = 0
            total_delivered = 0
            total_earned = 0

            for order in grinder_orders:
                total_claimed += 1
                total_earned += order["cost"]
                if order["status"] == "delivered":
                    total_delivered += 1

            total_earned = int(total_earned)

            embed.add_field(name="\u200b", value="__**Grinder Stats**__", inline=True)
            embed.add_field(name="Total Money Earned", value="${:,}".format(total_earned), inline=False)
            embed.add_field(name="Orders Claimed", value=total_claimed, inline=False)
            embed.add_field(name="Orders Delivered", value=total_delivered, inline=False)

            with open("db/items.json") as f:
                items = json.load(f)

            for role in user.roles:

                if role.id == grinder[1]:

                    total_claimed = 0
                    total_delivered = 0
                    total_earned = 0

                    for order in grinder_orders:
                        if items[order["product"]]["type"] == "BXP":
                            total_claimed += 1
                            total_earned += order["cost"]
                            if order["status"] == "delivered":
                                total_delivered += 1

                    total_earned = int(total_earned)

                    embed.add_field(name="\u200b", value="__**BXP Stats**__", inline=False)
                    embed.add_field(name="Total Money Earned", value="${:,}".format(total_earned), inline=False)
                    embed.add_field(name="Orders Claimed", value=total_claimed, inline=False)
                    embed.add_field(name="Orders Delivered", value=total_delivered, inline=False)

        con.close()
        await ctx.reply(embed=embed)

    #Errors
    @_claim.error
    async def claim_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.reply(embed=functions.embed_generator(self.bot, "The order ID must be a whole number", 0xff0000))
            return

    @_progress.error
    async def progress_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.reply(embed=functions.embed_generator(self.bot, "The order ID must be a whole number", 0xff0000))
            return

    @_delivered.error
    async def delivered_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.reply(embed=functions.embed_generator(self.bot, "The order ID must be a whole number", 0xff0000))
            return


def setup(bot):
    bot.add_cog(Grinder(bot))
