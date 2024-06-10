from functools import reduce

import discord
from discord.ext import commands

import config
import member.sheets as sheets_members
from member import rank
from utils.constants import SPIRIT_PURPLE, GROVE_GREEN

ANNOUNCEMENT_CHANNEL_ID = config.GROVE_CHANNEL_ID_LEADERBOARD

from member import common


async def send_leaderboard(bot: commands.Bot, interaction: discord.Interaction, emoji_id: str):
    sunday = common.sunday()
    guild_week = common.guild_week()
    leaderboard_week = sunday.strftime('%U')

    # Confirmation
    try:
        emoji = next(e for e in bot.emojis if str(e) == emoji_id)
    except StopIteration:
        await interaction.followup.send(
            'Error - invalid emoji, please use an emoji from this server. Announcement has been cancelled.')
        return

    confirmation_message_body = f'Are you sure you want to send the announcement in <#{ANNOUNCEMENT_CHANNEL_ID}>?\n\nWeek {guild_week}\n{sunday}\n{sunday.year} Leaderboard Week {leaderboard_week}\n{emoji_id}\n\n'

    class Buttons(discord.ui.View):
        def __init__(self, *, timeout=180):
            super().__init__(timeout=timeout)
            self.message = None
            self.interacted = False

        async def on_timeout(self) -> None:
            if not self.interacted:
                await self.message.edit(view=None)
                await interaction.followup.send('Error - Your command has timed out.')

        @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
        async def green_button(_self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id is not button_interaction.user.id:
                await button_interaction.response.send_message(
                    f'Error - This action can only be performed by {interaction.user.mention}.', ephemeral=True)
                return
            _self.interacted = True
            await button_interaction.response.edit_message(view=None)

            # Validate the spreadsheet has a column for this week's announcement
            if not sheets_members.is_valid(guild_week, sunday.strftime('%Y-%m-%d')):
                await interaction.followup.send(
                    'Error - unable to find the member tracking data for this week\'s announcement. Announcement has been cancelled.')
                return

            # Promotions to Tree and Spirit
            await interaction.followup.send('Promoting Spirit and Tree rank members...')

            spirit_promotions = []
            tree_promotions = []
            left_discord = []
            pre_promotions_mp_list = sheets_members.get_sorted_member_participation()
            for mp in pre_promotions_mp_list:
                if ((mp.rank == sheets_members.ROLE_NAME_TREE or mp.rank == sheets_members.ROLE_NAME_SAPLING)
                        and mp.contribution == sheets_members.CONTRIBUTION_THRESHOLD_SPIRIT and mp.ten_week_average >= sheets_members.AVERAGE_THRESHOLD_SPIRIT):
                    try:
                        await rank.spirit(interaction, bot.get_guild(config.GROVE_GUILD_ID).get_member(mp.discord_id))
                        spirit_promotions.append(mp)
                    except AttributeError:
                        left_discord.append(mp)
                elif mp.rank == sheets_members.ROLE_NAME_SAPLING and mp.contribution >= sheets_members.CONTRIBUTION_THRESHOLD_TREE:
                    try:
                        await rank.tree(interaction, bot.get_guild(config.GROVE_GUILD_ID).get_member(mp.discord_id))
                        tree_promotions.append(mp)
                    except AttributeError:
                        left_discord.append(mp)

            # Send to log channel
            member_activity_channel = bot.get_channel(config.GROVE_CHANNEL_ID_MEMBER_ACTIVITY)
            if len(spirit_promotions) > 0 or len(tree_promotions) > 0:
                promotions_message = f'# Week {guild_week} promotions\n'
                if len(spirit_promotions) > 0:
                    promotions_message += f'## <@&{config.GROVE_ROLE_ID_SPIRIT}> promotions\n'
                    for spirit in spirit_promotions:
                        promotions_message += f'- {spirit.grove_igns}\t{spirit.discord_mention}\n'
                if len(tree_promotions) > 0:
                    promotions_message += f'## <@&{config.GROVE_ROLE_ID_TREE}> promotions\n'
                    for tree in tree_promotions:
                        promotions_message += f'- {tree.grove_igns}\t{tree.discord_mention}\n'
                promotions_message += '\nPlease react when the above promotions have also been reflected in-game.'
                await member_activity_channel.send(promotions_message)

            if len(left_discord) > 0:
                left_discord_message = f'# Week {guild_week} leavers\n'
                for leaver in left_discord:
                    left_discord_message += f'- {leaver.grove_igns}\t{leaver.discord_mention}\n'
                left_discord_message += '\nPlease react when the above leavers have been removed from the guild and updated in the spreadsheet.'
                await member_activity_channel.send(left_discord_message)

            # Remove last week's Celestials
            await interaction.followup.send('Updating Celestials for the week...')

            celestial_role = bot.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_CELESTIAL)
            for member in celestial_role.members:
                await member.remove_roles(bot.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_CELESTIAL))

            # This week's Celestials
            mp_list = sheets_members.get_sorted_member_participation()
            new_celestials = _get_celestials(mp_list)

            for mp in new_celestials:
                member = bot.get_guild(config.GROVE_GUILD_ID).get_member(mp.discord_id)
                await member.add_roles(celestial_role)

            # Create and format announcement message
            await interaction.followup.send(f'Sending the announcement in <#{ANNOUNCEMENT_CHANNEL_ID}>...')
            announcement_body = f'Thanks everyone for another great week of Grove! Here\'s our week {guild_week} recap:\n<#LEADERBOARD_THREAD_ID_HERE>\n\n'

            # New members
            new_members = sheets_members.get_new_members()
            if len(new_members) == 0:
                pass
            elif len(new_members) == 1:
                announcement_body += f'Welcome to our new member this week:\n{new_members[0]}\n\n'
            else:
                announcement_body += 'Welcome to our new members this week:\n'
                announcement_body += reduce(lambda body, member: body + f'{member}\n', new_members, "")
                announcement_body += '\n'

            announcement_body += f'Happy Mapling, Go Grove! {emoji_id}'

            # Send announcement
            send_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
            announcement_message = await send_channel.send(content=announcement_body,
                                                           embeds=_get_announcement_embeds(guild_week, new_celestials,
                                                                                           spirit_promotions,
                                                                                           tree_promotions))
            await announcement_message.add_reaction(emoji)

            # Create leaderboard thread and add link to main announcement
            leaderboard_thread_title = f'{sunday.year} Culvert & Flag Race Leaderboard - Week {leaderboard_week}'
            leaderboard_thread = await announcement_message.create_thread(name=leaderboard_thread_title)
            announcement_body = announcement_body.replace('LEADERBOARD_THREAD_ID_HERE', f'{leaderboard_thread.id}')
            print(announcement_body)
            await announcement_message.edit(content=announcement_body)

            # Send leaderboard ranking messages
            await _announce_leaderboard(leaderboard_thread, leaderboard_thread_title, mp_list)

            # Set the new members as introed
            sheets_members.update_introed_new_members()

            await interaction.followup.send("Announcement complete!")

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
        async def red_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id is not button_interaction.user.id:
                await button_interaction.response.send_message(
                    f'Error - This action can only be performed by {interaction.user.mention}.', ephemeral=True)
                return
            self.interacted = True
            await button_interaction.response.edit_message(view=None)
            await interaction.followup.send('Announcement has been cancelled.')

    buttons_view = Buttons()
    buttons_view.message = await interaction.followup.send(confirmation_message_body, view=buttons_view)


async def _announce_leaderboard(leaderboard_thread, leaderboard_thread_title,
                                mp_list: list[sheets_members.MemberParticipation]):
    await leaderboard_thread.send(f'# {leaderboard_thread_title}')
    leaderboard_embeds = _get_leaderboard_embeds(mp_list)
    for embed in leaderboard_embeds:
        await leaderboard_thread.send(embed=embed)
    await leaderboard_thread.send(
        f'*If you notice an error or have any questions or feedback, please let a <@&{config.GROVE_ROLE_ID_JUNIOR}> know. Thank you!*')


def _get_leaderboard_embeds(mp_list: list[sheets_members.MemberParticipation]):
    embeds = []
    current_score = None
    line = ''
    for mp in mp_list:
        if current_score is None:
            current_score = mp.score

        elif current_score != mp.score:
            if line != '':
                embeds.append(discord.Embed(title=f'{current_score} Points', description=line, colour=GROVE_GREEN))
            current_score = mp.score
            line = ''
        line += f'{mp.discord_mention} '

    if current_score is not None and line != '':
        embeds.append(discord.Embed(title=f'{current_score} Points', description=line, colour=GROVE_GREEN))

    return embeds


def _get_celestials(mp_list: list[sheets_members.MemberParticipation]):
    return list(filter(
        lambda mp: (mp.rank == sheets_members.ROLE_NAME_WARDEN
                    or mp.rank == sheets_members.ROLE_NAME_GUARDIAN
                    or mp.rank == sheets_members.ROLE_NAME_SPIRIT) and mp.ten_week_average >= sheets_members.AVERAGE_THRESHOLD_SPIRIT,
        mp_list))


def _get_announcement_embeds(guild_week: int,
                             celestials: list[sheets_members.MemberParticipation],
                             spirit_promotions: list[sheets_members.MemberParticipation],
                             tree_promotions: list[sheets_members.MemberParticipation]):
    announcement_embeds = []
    if len(celestials) > 0:
        announcement_embeds.append(_get_celestial_embed(guild_week, celestials))
    if len(spirit_promotions) > 0 or len(tree_promotions) > 0:
        announcement_embeds.append(_get_promotions_embed(guild_week, spirit_promotions, tree_promotions))

    return announcement_embeds


def _get_celestial_embed(guild_week: int,
                         celestials: list[sheets_members.MemberParticipation]):
    description = f'Special thanks this week\'s <@&{config.GROVE_ROLE_ID_CELESTIAL}> Grovians:\n'
    description += reduce(
        lambda body, member: body + f'{member.discord_mention} <:celestial:1174736926364934275>\n',
        celestials,
        "")
    description += '\n'
    return discord.Embed(title=f'Week {guild_week} Celestials', description=description, colour=SPIRIT_PURPLE)


def _get_promotions_embed(guild_week: int,
                          spirit_promotions: list[sheets_members.MemberParticipation],
                          tree_promotions: list[sheets_members.MemberParticipation]):
    embed = discord.Embed(title=f'Week {guild_week} Promotions')
    if len(spirit_promotions) > 0:
        embed.add_field(name='',
                        value=reduce(lambda body, member: body + f'{member.discord_mention}\n', spirit_promotions,
                                     f'<@&{config.GROVE_ROLE_ID_SPIRIT}>\n'))
    if len(tree_promotions) > 0:
        embed.add_field(name='',
                        value=reduce(lambda body, member: body + f'{member.discord_mention}\n', tree_promotions,
                                     f'<@&{config.GROVE_ROLE_ID_TREE}>\n'))
    return embed
