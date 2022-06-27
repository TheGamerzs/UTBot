import json
import sqlite3
import time

import discord


def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def discount_active():
    con = sqlite3.connect('db/orders.db')
    con.row_factory = dict_factory
    cur = con.cursor()

    cur.execute("SELECT discount_id, discount_amount, discount_end_date FROM discount WHERE active = 1")
    discount = cur.fetchone()

    if discount is None:
        con.close()
        return [False, 0]

    if discount["discount_end_date"] < int(time.time()):
        cur.execute("UPDATE discount SET active = 0 WHERE active = 1")
        con.commit()
        con.close()
        return [False, 0]

    con.close()
    return [discount["discount_id"], discount["discount_amount"]]

def discount_price(price):
    con = sqlite3.connect('db/orders.db')
    con.row_factory = dict_factory
    cur = con.cursor()

    cur.execute("SELECT discount_amount FROM discount WHERE active = 1")
    discount = cur.fetchone()
    con.close()
    if not discount:
        return price

    return int(round(price * (1 - (discount["discount_amount"] / 100))))

def discount_get_amount(id):
    con = sqlite3.connect('db/orders.db')
    con.row_factory = dict_factory
    cur = con.cursor()

    cur.execute("SELECT discount_amount FROM discount WHERE discount_id = ?", (id,))
    discount = cur.fetchone()
    con.close()
    if not discount:
        return False
    return discount["discount_amount"]

def embed_generator(bot, description, colour = 0x00FF00, author = None, avatar_url = None):
    if author is None:
        author = bot.user.name
    if avatar_url is None:
        avatar_url = bot.user.avatar_url
    embed = discord.Embed(description=description, colour=colour)
    embed.set_author(name=author, icon_url=avatar_url)
    return embed

def hunter_role():
    with open("db/config.json") as fp:
        config = json.load(fp)
    return config["hunter_role"]

def bxp_role():
    with open("db/config.json") as fp:
        config = json.load(fp)
    return config["bxp_role"]
