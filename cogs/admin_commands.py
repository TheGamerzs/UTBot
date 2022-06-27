import json
import re
import sqlite3
import time
from datetime import datetime, timedelta

import discord
import modules.functions as functions
from discord.ext import commands

tym = datetime.utcnow()

def manager_role():
    with open("db/config.json") as fp:
        config = json.load(fp)
    return config['manager_role']

class Admin(commands.Cog):
    """Admin Commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="cancel")
    @commands.has_role(manager_role())
    async def _cancel(self, ctx, order_id: int):
        """- Cancel an order"""
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
            await ctx.reply(embed=functions.embed_generator(self.bot, "This order is already cancelled", colour=0x23272A))
            con.close()
            return

        with open("db/config.json") as fp:
            config = json.load(fp)

        orders_channel = await self.bot.fetch_channel(config["orders_channel"])

        try:
            message = await orders_channel.fetch_message(order["messageid"])
            await message.delete()
        except discord.errors.NotFound:
            pass

        cur.execute("UPDATE orders SET status = 'cancelled' WHERE order_id LIKE ?", (order_id,))
        con.commit()
        con.close()

        await ctx.reply(embed=functions.embed_generator(self.bot, "You have successfully cancelled order #{}".format(order_id)))

        # Log the cancel
        log_channel = await self.bot.fetch_channel(config["log_channel"])
        await log_channel.send(embed=functions.embed_generator(self.bot, "Order #{} has been cancelled by {}".format(order_id, ctx.author.mention)))

    @commands.command(name="display")
    @commands.has_role(manager_role())
    async def _display(self, ctx, order_id: int):
        """- Display an order"""
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
            await ctx.reply(embed=functions.embed_generator(self.bot, "This order is already cancelled", colour=0x23272A))
            con.close()
            return

        with open("db/config.json") as fp:
            config = json.load(fp)

        with open("db/items.json") as fp:
            items = json.load(fp)

        orders_channel = await self.bot.fetch_channel(config["orders_channel"])

        # Send the order
        formatted_cost = "${:,}".format(order["cost"])
        embed = discord.Embed(title="{} Order Placed - #{}".format(items[order['product']]['type'], order_id), description="**Customer: **<@{}> ({})\n**Item: **{}\n**Amount: **{}\n**Cost: **{}\n**Storage: **{}".format(order["customer"], order["customer"], order['product'], order["amount"], formatted_cost, order["storage"]), colour=0x23272A)

        msg = await orders_channel.send(embed=embed)

        # Update the order
        cur.execute("UPDATE orders SET messageid = ? WHERE order_id LIKE ?", (msg.id, order_id))
        con.commit()
        con.close()

    @commands.command(name="update", aliases=["up"])
    @commands.has_role(manager_role())
    async def _update(self, ctx, order_id: int, new_amount: str):
        """- Update an order with the new amount of items"""
        con = sqlite3.connect('db/orders.db')
        con.row_factory = functions.dict_factory
        cur = con.cursor()

        cur.execute("SELECT * FROM orders WHERE order_id LIKE ?", (order_id,))
        order = cur.fetchone()
        if not order:
            await ctx.reply(embed=functions.embed_generator(self.bot, "Order not found", colour=0xFF0000))
            con.close()
            return

        if order["status"] == "cancelled":
            await ctx.reply(embed=functions.embed_generator(self.bot, "This order is already cancelled", colour=0xFF0000))
            con.close()
            return

        try:
            new_amount = int(new_amount)
        except ValueError:
            await ctx.reply(embed=functions.embed_generator(self.bot, "Invalid amount", colour=0xFF0000))
            con.close()
            return

        if new_amount < 1:
            await ctx.reply(embed=functions.embed_generator(self.bot, "Invalid amount", colour=0xFF0000))
            con.close()
            return

        with open("db/config.json") as fp:
            config = json.load(fp)

        with open('db/items.json') as fp:
            items = json.load(fp)

        orders_channel = await self.bot.fetch_channel(config["orders_channel"])

        deleted = False

        try:
            message = await orders_channel.fetch_message(order["messageid"])
            await message.delete()
            deleted = True
        except discord.errors.NotFound:
            pass

        cost = items[order["product"]]["cost"] * new_amount

        if order["priority"] == "high":
            cost = cost * 1.2

        if new_amount > items[order["product"]]["limit"]:
            cost = cost * 1.05


        cur.execute("UPDATE orders SET amount = ?, cost = ? WHERE order_id LIKE ?", (new_amount, cost, order_id))
        con.commit()
        con.close()

        formatted_cost = "$" + format(cost, ",")

        if deleted:
            embed = discord.Embed(title="{} Order Placed - #{}".format(items[order["product"]]["type"], order_id), description="**Customer: **{} ({})\n**Item: **{}\n**Amount: **{}\n**Cost: **{}{}\n**Storage: **{}".format(order["customer"], order["customer"], order["product"], new_amount, formatted_cost, order["storage"]), colour=0x23272A)
            await orders_channel.send(embed=embed)
        else:
            if order["grinder"] is not None :
                grinder = await self.bot.fetch_user(order["grinder"])
                await grinder.send(embed=functions.embed_generator(self.bot, "The order {} has been updated to {}'s {}".format(order_id, new_amount, order['product']), colour=0xaaFFaa))

        customer = await self.bot.fetch_user(order["customer"])
        await customer.send(embed=functions.embed_generator(self.bot, "Your order has been updated to {}'s {}".format(new_amount, order['product']), colour=0xaaFFaa))

        await ctx.reply(embed=functions.embed_generator(self.bot, "You have successfully updated order #{}".format(order_id)))

        # Log the update
        await self.bot.get_channel(config["log_channel"]).send(embed=functions.embed_generator(self.bot, "Order #{} has been updated to `{}` products".format(order_id, new_amount), colour=0xaaFFaa))

    @commands.command(name="updatestorage", aliases=["upstor"])
    @commands.has_role(manager_role())
    async def _updatestorage(self, ctx, order_id: int, new_storage: str = None):
        """- Update an order with the new storage location"""
        con = sqlite3.connect('db/orders.db')
        con.row_factory = functions.dict_factory
        cur = con.cursor()

        cur.execute("SELECT * FROM orders WHERE order_id LIKE ?", (order_id,))
        order = cur.fetchone()
        if not order:
            await ctx.reply(embed=functions.embed_generator(self.bot, "Order not found", colour=0xFF0000))
            con.close()
            return

        if order["status"] == "cancelled":
            await ctx.reply(embed=functions.embed_generator(self.bot, "This order is already cancelled", colour=0xFF0000))
            con.close()
            return

        with open("db/config.json") as fp:
            config = json.load(fp)

        orders_channel = await self.bot.fetch_channel(config["orders_channel"])
        deleted = False

        try:
            message = await orders_channel.fetch_message(order["messageid"])
            await message.delete()
            deleted = True
        except discord.errors.NotFound:
            pass

        cur.execute("UPDATE orders SET storage = ? WHERE order_id LIKE ?", (new_storage, order_id))
        con.commit()
        con.close()

        if deleted:
            embed = discord.Embed(title="{} Order Placed - #{}".format(items[order["product"]]["type"], order_id), description="**Customer: **{} ({})\n**Item: **{}\n**Amount: **{}\n**Cost: **{}{}\n**Storage: **{}".format(order["customer"], order["customer"], items[order["product"]]["name"], order["amount"], order["cost"], new_storage), colour=0x23272A)
            await orders_channel.send(embed=embed)
        else:
            if order["grinder"] is not None :
                grinder = await self.bot.fetch_user(order["grinder"])
                await grinder.send(embed=functions.embed_generator(self.bot, "The order {} has been updated to {}".format(order_id, new_storage), colour=0xaaFFaa))

        customer = await self.bot.fetch_user(order["customer"])
        await customer.send(embed=functions.embed_generator(self.bot, "Your order #{} has been updated to {}".format(order_id, new_storage), colour=0xaaFFaa))

        await ctx.reply(embed=functions.embed_generator(self.bot, "You have successfully updated order #{}".format(order_id)))

        # Log the update
        await self.bot.get_channel(config["log_channel"]).send(embed=functions.embed_generator(self.bot, "Order #{} has been updated storage to `{}`".format(order_id, new_storage), colour=0xaaFFaa))

    @commands.command(name="newdiscount")
    @commands.has_role(manager_role())
    async def _newdiscount(self, ctx, discount: int, length: int):
        con = sqlite3.connect('db/orders.db')
        con.row_factory = functions.dict_factory
        cur = con.cursor()

        cur.execute("SELECT discount_end_date FROM discount WHERE active = 1")
        current_discount = cur.fetchone()
        if current_discount:
            if current_discount["discount_end_date"] < int(time.time()):
                cur.execute("UPDATE discount SET active = 0 WHERE active = 1")
                con.commit()
                con.close()
            else:
                await ctx.reply(embed=functions.embed_generator(self.bot, "There is already an active discount", colour=0xff0000))
                con.close()
                return

        cur.execute("INSERT INTO discount (active, discount_amount, discount_start_date, discount_end_date, manager) VALUES (?, ?, ?, ?, ?)", (1, discount, int(time.time()), int(time.time()) + length * 86400, ctx.author.id))
        con.commit()
        con.close()

        manager = ctx.author.nick if ctx.author.nick else ctx.author.name

        await ctx.send(embed=functions.embed_generator(self.bot, "The discount **{}** has started for {}% off, for the next {} days has now been applied\n**Ends:** <t:{}:R>".format(manager, discount, length, int(time.time()) + length * 86400), author=manager, avatar_url=ctx.author.avatar_url))

    @commands.command(name="discount")
    @commands.has_role(manager_role())
    async def _discount(self, ctx):
        con = sqlite3.connect('db/orders.db')
        con.row_factory = functions.dict_factory
        cur = con.cursor()

        cur.execute("SELECT discount_amount, discount_end_date, manager FROM discount WHERE active = 1")
        discount = cur.fetchone()
        if not discount:
            await ctx.send(embed=functions.embed_generator(self.bot, "There is no active discount", colour=0x23272A))
            con.close()
            return

        con.close()

        manager = await self.bot.fetch_user(discount["manager"])

        if not manager:
            await ctx.send(embed=functions.embed_generator(self.bot, "The manager of this discount has left the server", colour=0x23272A))

        await ctx.send(embed=functions.embed_generator(self.bot, "The current discount is **{}%** started by **{}**\n**Ends:** <t:{}:R>".format(discount["discount_amount"], manager.name, discount["discount_end_date"]), author=manager.name, avatar_url=manager.avatar_url))

    @commands.command(name="enddiscount")
    @commands.has_role(manager_role())
    async def _enddiscount(self, ctx):
        con = sqlite3.connect('db/orders.db')
        con.row_factory = functions.dict_factory
        cur = con.cursor()

        cur.execute("SELECT manager, discount_amount FROM discount WHERE active = 1")
        current_discount = cur.fetchone()
        if not current_discount:
            await ctx.reply(embed=functions.embed_generator(self.bot, "There is no active discount", colour=0x23272A))
            con.close()
            return

        cur.execute("UPDATE discount SET active = 0 WHERE active = 1")
        con.commit()
        con.close()

        manager = await self.bot.fetch_user(current_discount["manager"])

        if not manager:
            await ctx.reply(embed=functions.embed_generator(self.bot, "The manager of this discount has left the server", colour=0x23272A))

        await ctx.reply(embed=functions.embed_generator(self.bot, "The discount of **{}%** by **{}** has now been ended".format(current_discount["discount_amount"], manager.name), 0x23272A, author=manager.name, avatar_url=manager.avatar_url))

    @commands.command(name="say")
    @commands.has_role(manager_role())
    async def _say(self, ctx, channel, *, input):
        mentions = None
        split = input.split("++")
        try:
            channel=channel.strip("<>#",)
        except IndexError:
            pass
        if channel.isnumeric() == True or channel=="no":
            pass
        else:
            await ctx.send("Enter `#channel or no` before adding title and message \nThe correct usage is `>say [channel/no] [title]++[message]++[mentions](optional)`")
            return
        try:
            title = split[0]
            message = split[1]
        except IndexError:
            await ctx.send("You have forgot to enter a title or message. The correct usage is `>say [channel/no] [title]++[message]++[mentions](optional)`")
            return

        if channel=="no":
            channel=ctx
            await ctx.channel.purge(limit=1)
            pass
        else:
            if channel>="100000000000000000":
                await ctx.channel.purge(limit=1)
                channel = await self.bot.fetch_channel(channel)
                await ctx.send(f"message send to {channel.mention}.")
                pass
            else:
                await ctx.send("Unknown Channel entered")
                return

        embed = discord.Embed(title=f"{title}", description=f"{message}", color = 0x23272A, timestamp=datetime.utcnow())



        if mentions is None:
            await channel.send(embed = embed)

        elif mentions:
            await channel.send(mentions, embed = embed)


    #Errors
    @_cancel.error
    async def cancel_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.reply(embed=functions.embed_generator(self.bot, "The order ID must be a whole number", 0x23272A))
            return


def setup(bot):
    bot.add_cog(Admin(bot))
