import os
import botfunctions
import discord
from discord.ext import tasks
from dotenv import load_dotenv
import traceback

MAX_TITLE_LENGTH = 128
TRIMMED = "<trimmed>"

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL = int(os.getenv('DISCORD_CHANNEL'))

client = discord.Client()

@client.event
async def on_ready():
    updatelist = botfunctions.firstStart()
    if updatelist:
        await send_update_messages(updatelist)
    if not check_mod_updates.is_running():
        check_mod_updates.start()
    await client.change_presence(activity = discord.Activity(type=discord.ActivityType.watching, name="the mod pipes"))
    user = await client.fetch_user("247640901805932544")
    await user.send("Mod update bot started!")

@tasks.loop(minutes=1)
async def check_mod_updates():
    try:
        updatelist = botfunctions.checkUpdates()
        if updatelist != []:
            await send_update_messages(updatelist)
                      
    except discord.DiscordServerError:
        print("Discord server error")
        pass
    except:
        user = await client.fetch_user("247640901805932544")
        await user.send(traceback.format_exc())

async def send_update_messages(updatelist: list):
    for mod, tag in updatelist:
        name = mod[0]
        title = mod[2]
        owner = mod[3]
        version = mod[4]
        output = await create_embed(name, title, owner, version, tag)
        channel = client.get_channel(CHANNEL)
        await channel.send(embed=output)

async def create_embed(name: str, title: str, owner: str, version: str, tag: str):
    title = botfunctions.make_safe(title)
    if len(title) > MAX_TITLE_LENGTH:
        title = title[:MAX_TITLE_LENGTH - len(TRIMMED)] + TRIMMED
    owner = botfunctions.make_safe(owner)
    if tag == "u":
        embedtitle = f'**Updated mod:** \n{title}'
        color = 0x5865F2
    elif tag == "n":
        embedtitle = f'**New mod:** \n{title}'
        color = 0x2ECC71
    link = f'https://mods.factorio.com/mods/{owner}/{name}'.replace(" ", "%20")

    thumbnailURL = botfunctions.getThumbnail(name)

    embed = discord.Embed(title=embedtitle, color=color, url=link)
    embed.add_field(name="Author", value=owner, inline=True)
    embed.add_field(name="Version:", value=version, inline=True)
    if thumbnailURL is not None:
        embed.set_thumbnail(url=thumbnailURL)
    return embed

client.run(TOKEN)