import os
import botfunctions
import discord
from discord.ext import commands
from discord.ext import tasks
from dotenv import load_dotenv
import sqlite3
import traceback


DB_NAME = "mods.db"
extensions = ["commands, modupdates"]

intents = discord.Intents.none()
intents.guilds = True
intents.integrations = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('PREFIX') + " "
bot = commands.Bot(command_prefix="~", intents=intents)

@bot.event
async def on_ready():   #TODO: Merge with botfunctions.firstStart, convert to setup_hook? 
                        #https://gist.github.com/Rapptz/6706e1c8f23ac27c98cee4dd985c8120#extcommands-breaking-changes
    for extension in extensions:
        await bot.load_extension(extension)
    await sync_commands()

    guilds = bot.guilds
    updatelist = await botfunctions.firstStart(guilds)
    if updatelist:
        await send_update_messages(updatelist)
    if not check_mod_updates.is_running():
        check_mod_updates.start()
    await bot.change_presence(activity = discord.Activity(type=discord.ActivityType.watching, name="the mod pipes"))

    appinfo = await bot.application_info()
    owner = appinfo.owner
    await owner.send("Mod update bot started!")

@bot.event
async def on_guild_join(guild: discord.Guild):
    with await sqlite3.connect(DB_NAME) as con:
        with await con.cursor() as cur:
            cur.execute("INSERT OR IGNORE INTO guilds VALUES (?, ?, ?)", (str(guild.id), None, None))
            con.commit()

@bot.event
async def on_guild_remove(guild: discord.Guild):
    with await sqlite3.connect(DB_NAME) as con:
        with await con.cursor() as cur:
            cur.execute("DELETE FROM guilds WHERE id = (?)", [str(guild.id)])
            con.commit()

@tasks.loop(minutes=1) #TODO: Move to modupdates
async def check_mod_updates():
    try:
        updatelist = await botfunctions.checkUpdates()
        if updatelist != []:
            await send_update_messages(updatelist)
                      
    except discord.DiscordServerError:
        print("Discord server error")
        pass
    except:
        appinfo = await bot.application_info()
        owner = appinfo.owner
        await owner.send(traceback.format_exc())

async def sync_commands():
    await bot.tree.sync(guild=discord.Object(763041705024552990))

bot.run(TOKEN)