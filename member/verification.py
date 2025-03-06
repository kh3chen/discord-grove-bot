import asyncio

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
