#!/usr/bin/env python3

import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv
import sqlite3
import logging
import traceback

from misc import get_mods

if os.path.isfile("botlog.old.log"):
    os.remove("botlog.old.log")

if os.path.isfile("botlog.log"):
    os.rename("botlog.log", "botlog.old.log")

logging.basicConfig(filename="botlog.log", filemode = "w", format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)

DB_NAME = "mods.db"
extensions = []
logging.debug("Loading cogs")
for root, _, files in os.walk("cogs"):
    for file in files:
        path = os.path.join(root, file)
        if path.endswith(".py"):
            extensions.append(path.split(".py")[0].replace(os.sep, "."))
            logging.debug(f"Loaded cog: {path}")

intents = discord.Intents.none()
intents.guilds = True
intents.integrations = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('PREFIX') + " "

class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    async def setup_hook(self) -> None:
        logging.info("Bot starting up")
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            await self.make_or_update_tables(con, cur)
        for extension in extensions:
            await bot.load_extension(extension)

    async def on_ready(self):
        logging.info("Bot ready")
        await bot.tree.sync(guild=discord.Object(763041705024552990))
        await bot.change_presence(status=discord.Status.online, activity=discord.Game("Factorio"))
        appinfo = await self.application_info()
        self.owner = appinfo.owner
        await self.owner.send("Mod update bot started!")
    
    async def on_disconnect(self):
        logging.debug("Disconnected")
    
    async def on_connect(self):
        logging.debug("connected")

    async def on_guild_join(self, guild: discord.Guild):
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            cur.execute("INSERT OR IGNORE INTO guilds VALUES (?, ?, ?, ?)", (str(guild.id), None, None, None))
            con.commit()
        await self.owner.send("Joined guild")
        logging.info(f"Joined guild: {guild.id}")
        
    async def on_guild_remove(self, guild: discord.Guild):
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            cur.execute("DELETE FROM guilds WHERE id = (?)", [str(guild.id)])
            con.commit()
        logging.info(f"Left guild: {guild.id}")
    
    async def on_error(self, event):
        type, value, tb = sys.exc_info()
        logging.critical(f"Error in {event}\n{type}, {value}.")
        logging.debug(f"Trackback: {traceback.format_tb(tb)}")
        self.owner.send(f"Error in {event}\n{type}, {value}.\nTraceback: {traceback.format_tb(tb)}")
    
    async def make_or_update_tables(self, con, cur):
        #Check if guilds table exists, update or create if necessary
        guilds = [guild async for guild in bot.fetch_guilds(limit=150)]
        cur.execute(''' SELECT count(*) FROM sqlite_master WHERE type='table' AND name='guilds' ''')
        if cur.fetchone()[0]==1: #Guilds table already exists
            for guild in guilds: #Add guilds that were joined while bot was offline
                guildentries = cur.execute("SELECT * FROM guilds WHERE id = (?)", [str(guild.id)]).fetchall()
                if guildentries == []:
                    with sqlite3.connect(DB_NAME) as con:
                        cur = con.cursor()
                        cur.execute("INSERT OR IGNORE INTO guilds VALUES (?, ?, ?, ?)", (str(guild.id), None, None, None))
                        con.commit()
                    logging.info(f"Added guild on start: {guild.id}")
        else: #Guilds table does not yet exist
            logging.warning(f"New guilds table created. This is expected on a first start")
            cur.execute('''CREATE TABLE guilds
                        (id, updates_channel, modrole, subscribedmods, UNIQUE(id))''')
            for guild in guilds:
                guildentries = cur.execute("SELECT * FROM guilds WHERE id = (?)", [str(guild.id)]).fetchall()
                if guildentries == []:
                    with sqlite3.connect(DB_NAME) as con:
                        cur = con.cursor()
                        cur.execute("INSERT OR IGNORE INTO guilds VALUES (?, ?, ?, ?)", (str(guild.id), None, None, None))
                        con.commit()
                    logging.info(f"Added guild on start: {guild.id}")

        #Check if mods table exists, create if necessary
        cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='mods' ''')
        if cur.fetchone()[0]!=1: #Mods table does not yet exist - download full database and create database.
            logging.warning("New mods table created. This is expected on a first start.")
            url = "https://mods.factorio.com/api/mods?page_size=max"
            mods = await get_mods(url)
            cur.execute('''CREATE TABLE mods
                    (name, release_date, title, owner, version, UNIQUE(name))''')
            cur.executemany("INSERT OR IGNORE INTO mods VALUES (?, ?, ?, ?, ?)", mods)
            con.commit()

bot = MyBot(command_prefix=PREFIX, intents=intents)
bot.run(TOKEN)