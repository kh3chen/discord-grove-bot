from functools import reduce

import discord

import config
from member import sheets
from member.sheets import ROLE_NAME_SPIRIT, ROLE_NAME_TREE, ROLE_NAME_SAPLING, ROLE_NAME_MOSS, UpdateMemberRankResult


async def spirit(interaction: discord.Interaction, member: discord.Member):
    await __set_grove_role(interaction, member, config.GROVE_ROLE_ID_SPIRIT, ROLE_NAME_SPIRIT)


async def tree(interaction: discord.Interaction, member: discord.Member):
    await __set_grove_role(interaction, member, config.GROVE_ROLE_ID_TREE, ROLE_NAME_TREE)


async def sapling(interaction: discord.Interaction, member: discord.Member):
    update_member_rank_result = await __set_grove_role(interaction, member, config.GROVE_ROLE_ID_SAPLING,
                                                       ROLE_NAME_SAPLING)

    if update_member_rank_result == UpdateMemberRankResult.Success:
        # Welcome message
        member_welcome_channel = interaction.guild.get_channel(config.GROVE_CHANNEL_ID_MAPLE_CHAT)
        await member_welcome_channel.send(
            f'## Welcome to Grove, {member.mention}!'
            f'\n- Please update your Grove Discord nickname to **Preferred Name (IGN)**'
            f'\n- You can choose your visible channels and selected roles at <id:customize>'
            f'\n- Tell us a little about yourself in <#{config.GROVE_CHANNEL_ID_INTRODUCTIONS}>'
            f'\n\nReach out to any <@&{config.GROVE_ROLE_ID_JUNIOR}> for any questions you may have about MapleStory and our community! <:grove:924924448916795403>')


async def moss(interaction: discord.Interaction, member: discord.Member):
    await __set_grove_role(interaction, member, config.GROVE_ROLE_ID_MOSS, ROLE_NAME_MOSS)


async def __set_grove_role(interaction: discord.Interaction, member: discord.Member, grove_role_id: int,
                           grove_role_name: str):
    # Update spreadsheet
    update_member_rank_result = sheets.update_member_rank(member.id, grove_role_name)
    if update_member_rank_result == UpdateMemberRankResult.Success:

        await member.remove_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_SPIRIT),
                                  interaction.guild.get_role(config.GROVE_ROLE_ID_TREE),
                                  interaction.guild.get_role(config.GROVE_ROLE_ID_SAPLING),
                                  interaction.guild.get_role(config.GROVE_ROLE_ID_MOSS),
                                  interaction.guild.get_role(config.GROVE_ROLE_ID_GUEST),
                                  interaction.guild.get_role(config.GROVE_ROLE_ID_RETIREE))
        await member.add_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_GROVE),
                               interaction.guild.get_role(grove_role_id))

        await interaction.followup.send(f'{member.mention} is now a <@&{grove_role_id}>.')
    elif update_member_rank_result == UpdateMemberRankResult.NotFound:
        await interaction.followup.send(f'Error - {member.mention} has not been added to member tracking.')
    elif update_member_rank_result == UpdateMemberRankResult.NotVerified:
        await interaction.followup.send(f'Error - {member.mention} has not verified their main.')

    return update_member_rank_result


async def guest(interaction: discord.Interaction, member: discord.Member):
    await member.remove_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_GROVE),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_SPIRIT),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_TREE),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_SAPLING),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_MOSS),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_RETIREE))
    await member.add_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_GUEST))
    await interaction.followup.send(f'{member.mention} is now a <@&{config.GROVE_ROLE_ID_GUEST}>.')
    await track_past_member(interaction.guild.get_channel(config.GROVE_CHANNEL_ID_MEMBER_ACTIVITY), member,
                            'Left for another guild')


async def onboard_guest(guild: discord.Guild, member: discord.Member):
    await member.add_roles(guild.get_role(config.GROVE_ROLE_ID_GUEST))


async def retiree(interaction: discord.Interaction, member: discord.Member):
    await member.remove_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_GROVE),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_SPIRIT),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_TREE),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_SAPLING),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_MOSS),
                              interaction.guild.get_role(config.GROVE_ROLE_ID_GUEST))
    await member.add_roles(interaction.guild.get_role(config.GROVE_ROLE_ID_RETIREE))
    await interaction.followup.send(f'{member.mention} is now a <@&{config.GROVE_ROLE_ID_RETIREE}>.')
    await track_past_member(interaction.guild.get_channel(config.GROVE_CHANNEL_ID_MEMBER_ACTIVITY), member, 'Retiree')


async def track_past_member(member_activity_channel: discord.TextChannel, member: discord.Member, reason: str = 'TBD'):
    removed_member = sheets.remove_member(member.id, reason)
    if removed_member is not None:
        # Send to log channel
        removed_member_message = f'## {removed_member.discord_mention} removed'
        removed_member_message += f'\nReason: {reason}'
        removed_member_message += '\n'
        removed_member_message += '\n**Grove IGNs**'
        removed_member_message += '\n- '
        removed_member_message += reduce(lambda acc, val: acc + '\n- ' + val,
                                         removed_member.grove_igns.split('\n'))
        if removed_member.mule_igns != '':
            removed_member_message += '\n'
            removed_member_message += f'\n**Mule IGNs**'
            removed_member_message += '\n- '
            removed_member_message += reduce(lambda acc, val: acc + '\n- ' + val,
                                             removed_member.mule_igns.split('\n'))
        removed_member_message += '\n'
        removed_member_message += '\nPlease react when the above characters have been removed from the guild and the remove reason has been updated in the spreadsheet.'

        await member_activity_channel.send(removed_member_message)


async def audit_members(interaction: discord.Interaction):
    tracked_members = sheets.get_members()
    tracked_member_mentions = list(
        map(lambda tracked_member: tracked_member.discord_mention, tracked_members)) + config.GROVE_AUDIT_EXCEPTIONS
    bossing_guests = []
    retirees = []
    illegals = []
    for member in interaction.guild.members:
        if member.mention in tracked_member_mentions:
            # In our member tracking sheet
            continue

        member_role_ids = list(map(lambda role: role.id, member.roles))
        if config.GROVE_ROLE_ID_BOT in member_role_ids:
            # Bot role
            continue

        if config.GROVE_ROLE_ID_GUEST in member_role_ids:
            # Bossing Guest
            bossing_guests.append(member)
            continue

        if config.GROVE_ROLE_ID_RETIREE in member_role_ids:
            # Retiree
            retirees.append(member)
            continue

        illegals.append(member)

    message = "# Discord member audit results"
    message += '\n## Bossing Guests'
    if len(bossing_guests) > 0:
        for bossing_guest in bossing_guests:
            message += f'\n{bossing_guest.mention}'
    else:
        message += "\nNone"
    message += '\n## Retirees'
    if len(retirees) > 0:
        for retiree in retirees:
            message += f'\n{retiree.mention}'
    else:
        message += "\nNone"
    message += '\n## Illegal Members'
    if len(illegals) > 0:
        for illegal in illegals:
            message += f'\n{illegal.mention}'
    else:
        message += "\nNone"

    await interaction.followup.send(message)
