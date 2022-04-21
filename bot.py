import os
import botfunctions
import discord
from discord.ext import tasks
from dotenv import load_dotenv
import traceback

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL = int(os.getenv('DISCORD_CHANNEL'))

client = discord.Client()

@client.event
async def on_ready():
    updatelist = botfunctions.firstStart()
    if updatelist:
        await send_update_messages(updatelist)
    check_mod_updates.start()
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

async def send_update_messages(updatelist):
    for mod, tag in updatelist:
        name = mod[0]
        title = mod[2]
        owner = mod[3]
        version = mod[4]
        output = botfunctions.singleMessageLine(name, title, owner, version, tag)
        channel = client.get_channel(CHANNEL)
        await channel.send(output)

client.run(TOKEN)