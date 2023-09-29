import discord

import config


async def spirit(interaction: discord.Interaction, member: discord.Member):
    await __set_grove_role(interaction, member, config.GROVE_ROLE_ID_SPIRIT)


async def tree(interaction: discord.Interaction, member: discord.Member):
    await __set_grove_role(interaction, member, config.GROVE_ROLE_ID_TREE)


async def sapling(interaction: discord.Interaction, member: discord.Member):
    await __set_grove_role(interaction, member, config.GROVE_ROLE_ID_SAPLING)


async def moss(interaction: discord.Interaction, member: discord.Member):
    await __set_grove_role(interaction, member, config.GROVE_ROLE_ID_MOSS)


async def __set_grove_role(interaction: discord.Interaction, member: discord.Member, grove_role_id: int):
    await __remove_all_grove_roles(interaction, member)
    await member.add_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_GROVE),
                           interaction.guild.get_role(grove_role_id))
    # Update spreadsheet

    await interaction.followup.send(f'{member.mention} is now a <@&{grove_role_id}>.')


async def guest(interaction: discord.Interaction, member: discord.Member):
    await __remove_all_grove_roles(interaction, member)
    await member.add_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_GUEST))
    await interaction.followup.send(f'{member.mention} is now a <@&{config.GROVE_ROLE_ID_GUEST}>.')


async def __remove_all_grove_roles(interaction: discord.Interaction, member: discord.Member):
    await member.remove_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_GROVE),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_SPIRIT),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_TREE),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_SAPLING),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_MOSS),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_GUEST))
