import os
import botfunctions
import discord
from discord.ext import tasks
from discord.ext import commands
from dotenv import load_dotenv
import traceback

MAX_TITLE_LENGTH = 128
TRIMMED = "<trimmed>"

intents = discord.Intents.none()
intents.guilds = True
intents.guild_messages = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('PREFIX') + " "
bot = commands.Bot(command_prefix = PREFIX, intents = intents)

@bot.event
async def on_ready():
    guilds = bot.guilds
    updatelist = await botfunctions.firstStart(guilds)
    if updatelist:
        await send_update_messages(updatelist)
    if not check_mod_updates.is_running():
        check_mod_updates.start()
    await bot.change_presence(activity = discord.Activity(type=discord.ActivityType.watching, name="the mod pipes"))
    user = await bot.fetch_user("247640901805932544")
    await user.send("Mod update bot started!")

@bot.command()
async def set_channel(ctx, id):
    if id[0:2] == "<#":
        id = id[2:-1]
    if id.isnumeric():
        id = int(id)
        channel = bot.get_channel(id)
        if channel.guild == ctx.guild:
            await botfunctions.setChannel(ctx.guild.id, id)
            await ctx.send(f"Mod updates channel set to <#{id}>")
        else:
            await ctx.send("Invalid argument, please use a channel on this server")
    else:
        await ctx.send("Invalid argument, please use a channel link or ID")

@bot.command()
async def invite(ctx):
    await ctx.send("https://discord.com/api/oauth2/authorize?client_id=872540831599456296&permissions=19456&scope=bot")

@bot.event
async def on_guild_join(guild):
    await botfunctions.addGuild(guild.id)

@bot.event
async def on_guild_remove(guild):
    await botfunctions.removeGuild(guild.id)

@tasks.loop(minutes=1)
async def check_mod_updates():
    try:
        updatelist = await botfunctions.checkUpdates()
        if updatelist != []:
            await send_update_messages(updatelist)
                      
    except discord.DiscordServerError:
        print("Discord server error")
        pass
    except:
        user = await bot.fetch_user("247640901805932544")
        await user.send(traceback.format_exc())

async def send_update_messages(updatelist: list):
    for mod, tag in updatelist:
        name = mod[0]
        title = mod[2]
        owner = mod[3]
        version = mod[4]
        output = await create_embed(name, title, owner, version, tag)
        channels = await botfunctions.getChannels()
        for channelID in channels:
            channel = bot.get_channel(int(channelID[0]))
            await channel.send(embed=output)

async def create_embed(name: str, title: str, owner: str, version: str, tag: str):
    title = await botfunctions.make_safe(title)
    if len(title) > MAX_TITLE_LENGTH:
        title = title[:MAX_TITLE_LENGTH - len(TRIMMED)] + TRIMMED
    owner = await botfunctions.make_safe(owner)
    if tag == "u":
        embedtitle = f'**Updated mod:** \n{title}'
        color = 0x5865F2
    elif tag == "n":
        embedtitle = f'**New mod:** \n{title}'
        color = 0x2ECC71
    link = f'https://mods.factorio.com/mods/{owner}/{name}'.replace(" ", "%20")

    thumbnailURL = await botfunctions.getThumbnail(name)

    embed = discord.Embed(title=embedtitle, color=color, url=link)
    embed.add_field(name="Author", value=owner, inline=True)
    embed.add_field(name="Version:", value=version, inline=True)
    if thumbnailURL is not None:
        embed.set_thumbnail(url=thumbnailURL)
    return embed

bot.run(TOKEN)