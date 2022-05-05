#!/usr/bin/env python3

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import sqlite3
from misc import get_mods

DB_NAME = "mods.db"
extensions = ["commands", "modupdates"]

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
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            await self.make_or_update_tables(con, cur)
        for extension in extensions:
            await bot.load_extension(extension)

    async def on_ready(self):
        await bot.tree.sync(guild=discord.Object(763041705024552990))
        await bot.change_presence(status=discord.Status.online, activity=discord.Game("Factorio"))
        appinfo = await self.application_info()
        owner = appinfo.owner
        await owner.send("Mod update bot started!")

    async def on_guild_join(guild: discord.Guild):
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            cur.execute("INSERT OR IGNORE INTO guilds VALUES (?, ?, ?, ?)", (str(guild.id), None, None, None))
            con.commit()
        
    async def on_guild_remove(guild: discord.Guild):
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            cur.execute("DELETE FROM guilds WHERE id = (?)", [str(guild.id)])
            con.commit()
    
    async def make_or_update_tables(self, con, cur):
        #Check if guilds table exists, update or create if necessary
        guilds = [guild async for guild in bot.fetch_guilds(limit=150)]
        cur.execute(''' SELECT count(*) FROM sqlite_master WHERE type='table' AND name='guilds' ''')
        if cur.fetchone()[0]==1: #Guilds table already exists
            for guild in guilds: #Add guilds that were joined while bot was offline
                guildentries = cur.execute("SELECT * FROM guilds WHERE id = (?)", [str(guild.id)]).fetchall()
                if guildentries == []:
                    await self.addGuild(guild.id)
        else: #Guilds table does not yet exist
            cur.execute('''CREATE TABLE guilds
                        (id, updates_channel, modrole, subscribedmods, UNIQUE(id))''')
            for guild in guilds:
                guildentries = cur.execute("SELECT * FROM guilds WHERE id = (?)", [str(guild.id)]).fetchall()
                if guildentries == []:
                    with sqlite3.connect(DB_NAME) as con:
                        cur = con.cursor()
                        cur.execute("INSERT OR IGNORE INTO guilds VALUES (?, ?, ?, ?)", (str(guild.id), None, None, None))
                        con.commit()

        #Check if mods table exists, create if necessary
        cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='mods' ''')
        if cur.fetchone()[0]!=1: #Mods table does not yet exist - download full database and create database.
            url = "https://mods.factorio.com/api/mods?page_size=max"
            mods = await get_mods(url)
            cur.execute('''CREATE TABLE mods
                    (name, release_date, title, owner, version, UNIQUE(name))''')
            cur.executemany("INSERT OR IGNORE INTO mods VALUES (?, ?, ?, ?, ?)", mods)
            con.commit()

bot = MyBot(command_prefix=PREFIX, intents=intents)
bot.run(TOKEN)