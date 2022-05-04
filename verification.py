import discord
import sqlite3

DB_NAME = "mods.db"

async def verify_user(interaction: discord.Interaction) -> bool:
    '''
    Verifies if users are either admin or have the proper role to interact with the restricted bot commands.
    '''
    permissions = interaction.channel.permissions_for(interaction.user)
    if permissions.administrator:
        return True
    else:
        with await sqlite3.connect(DB_NAME) as con:
            with await con.cursor() as cur:
                roles = await cur.execute("SELECT modrole FROM guilds WHERE id = (?)", [str(interaction.guild.id)]).fetchall()
                servermodrole =  roles[0][0]
        userroles = [str(role.id) for role in interaction.user.roles]
        if servermodrole in userroles:
            return True
        else:
            await interaction.response.send_message("You do not have the right permissions for this", ephemeral=True)
            return False