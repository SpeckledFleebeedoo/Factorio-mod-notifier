import os
import botfunctions
import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv
import traceback

MAX_TITLE_LENGTH = 128
TRIMMED = "<trimmed>"

MY_GUILD_ID = os.getenv('MY_GUILD_ID') #MUST BE REMOVED FOR PUBLIC BOT

intents = discord.Intents.none()
intents.guilds = True
intents.integrations = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('PREFIX') + " "
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    guilds = client.guilds
    updatelist = await botfunctions.firstStart(guilds)
    if updatelist:
        await send_update_messages(updatelist)
    if not check_mod_updates.is_running():
        check_mod_updates.start()
    await client.change_presence(activity = discord.Activity(type=discord.ActivityType.watching, name="the mod pipes"))
    await sync_commands()
    appinfo = await client.application_info()
    owner = appinfo.owner
    await owner.send("Mod update bot started!")

async def verify_user(interaction: discord.Interaction) -> bool:
    '''
    Verifies if users are either admin or have the proper role to interact with the restricted bot commands.
    '''
    permissions = interaction.channel.permissions_for(interaction.user)
    if permissions.administrator:
        return True
    else:
        servermodrole = await botfunctions.getModRole(str(interaction.guild.id))
        userroles = [str(role.id) for role in interaction.user.roles]
        if servermodrole in userroles:
            return True
        else:
            await interaction.response.send_message("You do not have the right permissions for this", ephemeral=True)
            return False

@tree.command(guild=discord.Object(id=MY_GUILD_ID))
@discord.app_commands.check(verify_user)
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    '''
    Sets the channel in which mod updates are posted.
    '''
    await botfunctions.setChannel(interaction.guild.id, channel.id)
    await interaction.response.send_message(f"Mod updates channel set to <#{channel.id}>", ephemeral=True)


@tree.command(guild=discord.Object(id=MY_GUILD_ID))
@discord.app_commands.check(verify_user)
async def set_modrole(interaction: discord.Interaction, role: discord.Role):
    '''
    Sets the role needed to change bot settings. Server admins always can.
    '''
    await botfunctions.setModRole(interaction.guild.id, role.id)
    await interaction.response.send_message(f"Modrole set to <@&{role.id}>", ephemeral=True)

@tree.command(guild=discord.Object(id=MY_GUILD_ID))
async def invite(interaction:discord.Interaction):
    '''
    Posts an invite link for adding the bot to another server.
    '''
    await interaction.response.send_message("https://discord.com/api/oauth2/authorize?client_id=872540831599456296&permissions=19456&scope=bot")

@client.event
async def on_guild_join(guild):
    await botfunctions.addGuild(guild.id)

@client.event
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
        appinfo = await client.application_info()
        owner = appinfo.owner
        await owner.send(traceback.format_exc())

async def send_update_messages(updatelist: list):
    for mod, tag in updatelist:
        name = mod[0]
        title = mod[2]
        owner = mod[3]
        version = mod[4]
        output = await create_embed(name, title, owner, version, tag)
        channels = await botfunctions.getChannels()
        for channelID in channels:
            channel = client.get_channel(int(channelID[0]))
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

async def sync_commands():
    await tree.sync(guild=discord.Object(id=MY_GUILD_ID))

client.run(TOKEN)