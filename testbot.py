import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="~", intents=intents)

@bot.event
async def on_ready():
    await bot.load_extension("commands")
    await bot.tree.sync()
    print("ready")

bot.run(TOKEN)