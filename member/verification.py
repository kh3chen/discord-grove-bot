import discord

import config


async def create_verification_thread(guild: discord.guild, member: discord.member, command=False):
    if not command and member.voice is not None:
        # If they are in a VC, assume they joined using a VC link.
        # This is a temporary bossing guest and will be removed automatically
        return

    await member.add_roles(guild.get_role(config.GROVE_ROLE_ID_UNVERIFIED))
    verification_channel = guild.get_channel(config.GROVE_CHANNEL_ID_VERIFICATION)
    verification_thread = await verification_channel.create_thread(name=f'{member.name} verification',
                                                                   type=discord.ChannelType.private_thread)
    message = (
        f'Hi {member.mention}, welcome to Grove! A <@&{config.GROVE_ROLE_ID_JUNIOR}> will be connecting with you '
        f'shortly for your verification. In the meantime, please provide your MapleStory character name, and tell us '
        f'if you are here as a new member or bossing guest!')
    await verification_thread.send(message)
    return verification_thread


async def create_reverification_thread(interaction: discord.Interaction, member: discord.member, new_main_ign: str):
    await member.remove_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_GROVE))
    await member.add_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_UNVERIFIED))
    verification_channel = interaction.guild.get_channel(config.GROVE_CHANNEL_ID_VERIFICATION)
    verification_thread = await verification_channel.create_thread(name=f'{member.name} re-verification',
                                                                   type=discord.ChannelType.private_thread)

    if new_main_ign is not None:
        template = (
            f'\nHi {member.mention}, we recently noticed that your character, **{new_main_ign}**, is your most active '
            f'character and is not in Grove or any of our mule guilds. Since having a main in Grove is our only '
            f'requirement, your access to guild skills on Grove has been revoked, and any bossing mules have been '
            f'removed from our mule guilds.'
            f'\n'
            f'\nIf you would like to stay in Grove, please apply to Grove on your new main, **{new_main_ign}**. Thank you!')
    else:
        template = (
            f'\nHi {member.mention}, we recently noticed that you do not have a character in Grove or any of our mule '
            f'guilds with visible legion. This indicates to us that you have a new main outside of Grove. Since having a '
            f'main in Grove is our only requirement, your access to guild skills on Grove has been revoked, and any '
            f'bossing mules have been removed from our mule guilds.'
            f'\n'
            f'\nIf you would like to stay in Grove, please apply to Grove on your new main. Thank you!')

    message = (
        f'Re-verification thread: {verification_thread.mention}'
        f'\n'
        f'\nMessage template:'
        f'\n```{template}```'
        f'\n'
        f'\nUse the `/mod-reverify-success` command to complete successful re-verification.')
    await interaction.followup.send(message)


async def reverify_success(interaction: discord.Interaction, member: discord.member, new_main_ign: str):
    if interaction.guild.get_role(config.GROVE_ROLE_ID_UNVERIFIED) in member.roles:
        if (interaction.guild.get_role(config.GROVE_ROLE_ID_SPIRIT) in member.roles or
                interaction.guild.get_role(config.GROVE_ROLE_ID_SPIRIT) in member.roles or
                interaction.guild.get_role(config.GROVE_ROLE_ID_SPIRIT) in member.roles):
            member.remove_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_UNVERIFIED))
            member.add_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_GROVE))
            await interaction.followup.send(
                f'{member.mention} has completed re-verification. New main: **{new_main_ign}**')
        else:
            await interaction.followup.send(
                f'Error - {member.mention} is not eligible for re-verification. Please complete initial verification.')
    else:
        await interaction.followup.send(
            f'Error - {member.mention} is already verified.')
