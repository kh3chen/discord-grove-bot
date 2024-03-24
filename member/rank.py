import discord

import config
from member import sheets
from member.sheets import ROLE_NAME_SPIRIT, ROLE_NAME_TREE, ROLE_NAME_SAPLING, ROLE_NAME_MOSS


async def spirit(interaction: discord.Interaction, member: discord.Member):
    await __set_grove_role(interaction, member, config.GROVE_ROLE_ID_SPIRIT, ROLE_NAME_SPIRIT)


async def tree(interaction: discord.Interaction, member: discord.Member):
    await __set_grove_role(interaction, member, config.GROVE_ROLE_ID_TREE, ROLE_NAME_TREE)


async def sapling(interaction: discord.Interaction, member: discord.Member):
    sapling_role_given = await __set_grove_role(interaction, member, config.GROVE_ROLE_ID_SAPLING, ROLE_NAME_SAPLING)

    if sapling_role_given:
        # Welcome message
        member_welcome_channel = interaction.guild.get_channel(config.GROVE_CHANNEL_ID_MAPLE_CHAT)
        await member_welcome_channel.send(
            f'**Welcome to Grove, {member.mention}!**'
            f'\n'
            f'\nPlease update your Grove Discord nickname to **Preferred Name (IGN)**. You can ping <@&{config.GROVE_ROLE_ID_JUNIOR}> for any questions you may have about MapleStory and our community! <:grove:924924448916795403>')


async def moss(interaction: discord.Interaction, member: discord.Member):
    await __set_grove_role(interaction, member, config.GROVE_ROLE_ID_MOSS, ROLE_NAME_MOSS)


async def __set_grove_role(interaction: discord.Interaction, member: discord.Member, grove_role_id: int,
                           grove_role_name: str):
    # Update spreadsheet
    member_exists = sheets.update_member_rank(member.id, grove_role_name)
    if member_exists:

        await member.remove_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_SPIRIT),
                                  interaction.guild.get_role(config.GROVE_ROLE_ID_TREE),
                                  interaction.guild.get_role(config.GROVE_ROLE_ID_SAPLING),
                                  interaction.guild.get_role(config.GROVE_ROLE_ID_MOSS),
                                  interaction.guild.get_role(config.GROVE_ROLE_ID_GUEST),
                                  interaction.guild.get_role(config.GROVE_ROLE_ID_RETIREE))
        await member.add_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_GROVE),
                               interaction.guild.get_role(grove_role_id))

        await interaction.followup.send(f'{member.mention} is now a <@&{grove_role_id}>.')
    else:
        await interaction.followup.send(f'Error - {member.mention} has not been added to member tracking.')

    return member_exists


async def guest(interaction: discord.Interaction, member: discord.Member):
    await member.remove_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_GROVE),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_SPIRIT),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_TREE),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_SAPLING),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_MOSS),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_RETIREE))
    await member.add_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_GUEST))
    await interaction.followup.send(f'{member.mention} is now a <@&{config.GROVE_ROLE_ID_GUEST}>.')


async def retiree(interaction: discord.Interaction, member: discord.Member):
    await member.remove_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_GROVE),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_SPIRIT),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_TREE),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_SAPLING),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_MOSS),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_GUEST))
    await member.add_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_RETIREE))
    await interaction.followup.send(f'{member.mention} is now a <@&{config.GROVE_ROLE_ID_RETIREE}>.')
