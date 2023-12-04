import datetime
from functools import reduce

import discord
from discord.ext import commands

import config
import member.sheets as sheets_members
from member import rank

GUILD_CREATED_ON = datetime.date(2021, 12, 19)
ANNOUNCEMENT_CHANNEL_ID = config.GROVE_CHANNEL_ID_ANNOUNCEMENTS


async def send_announcement(bot: commands.Bot, interaction: discord.Interaction, emoji_id: str, custom_message_id: str):
    today = datetime.date.today()
    sunday = today - datetime.timedelta(days=(today.weekday() + 1) % 7)
    guild_week = (sunday - GUILD_CREATED_ON).days // 7
    leaderboard_week = sunday.strftime('%U')

    # Confirmation
    try:
        emoji = next(e for e in bot.emojis if str(e) == emoji_id)
    except StopIteration:
        await interaction.followup.send(
            'Error - invalid emoji, please use an emoji from this server. Announcement has been cancelled.')
        return

    custom_message = None
    if custom_message_id:
        channel = bot.get_channel(interaction.channel_id)
        custom_message = await channel.fetch_message(custom_message_id)

    confirmation_message_body = f'Are you sure you want to send the announcement in <#{ANNOUNCEMENT_CHANNEL_ID}>?\n\nWeek {guild_week}\n{sunday}\n{sunday.year} Leaderboard Week {leaderboard_week}\n{emoji_id}\n\n'
    if custom_message:
        confirmation_message_body += f'Custom message:\n```{custom_message.content}```\n\n'

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
            pre_promotions_wp_list = sheets_members.get_weekly_participation()
            for wp in pre_promotions_wp_list:
                if ((wp.rank == sheets_members.ROLE_NAME_TREE or wp.rank == sheets_members.ROLE_NAME_SAPLING)
                        and wp.contribution == sheets_members.CONTRIBUTION_THRESHOLD_SPIRIT and wp.ten_week_average >= sheets_members.AVERAGE_THRESHOLD_SPIRIT):
                    try:
                        await rank.spirit(interaction, bot.get_guild(config.GROVE_GUILD_ID).get_member(wp.discord_id))
                        spirit_promotions.append(wp)
                    except AttributeError:
                        left_discord.append(wp)
                elif wp.rank == sheets_members.ROLE_NAME_SAPLING and wp.contribution >= sheets_members.CONTRIBUTION_THRESHOLD_TREE:
                    try:
                        await rank.tree(interaction, bot.get_guild(config.GROVE_GUILD_ID).get_member(wp.discord_id))
                        tree_promotions.append(wp)
                    except AttributeError:
                        left_discord.append(wp)

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
            wp_list = sheets_members.get_weekly_participation()
            new_celestials = get_celestials(wp_list)

            for wp in new_celestials:
                member = bot.get_guild(config.GROVE_GUILD_ID).get_member(wp.discord_id)
                await member.add_roles(celestial_role)

            # Create and format announcement message
            await interaction.followup.send(f'Sending the announcement in <#{ANNOUNCEMENT_CHANNEL_ID}>...')
            announcement_body = f'<@&{config.GROVE_ROLE_ID_GROVE}>\n\nThanks everyone for another great week of Grove! Here\'s our week {guild_week} recap:\n<#LEADERBOARD_THREAD_ID_HERE>\n\n'

            if len(new_celestials) == 0:
                pass
            else:
                announcement_body += f'Special thanks this week\'s <@&{config.GROVE_ROLE_ID_CELESTIAL}> Grovians:\n'
                announcement_body = reduce(
                    lambda body, member: body + f'{member.discord_mention} <:celestial:1174736926364934275>\n',
                    new_celestials,
                    announcement_body)
                announcement_body += '\n'

            # New members
            new_members = sheets_members.get_new_members()
            if len(new_members) == 0:
                pass
            elif len(new_members) == 1:
                announcement_body += f'Welcome to our new member this week:\n{new_members[0]}\n\n'
            else:
                announcement_body += 'Welcome to our new members this week:\n'
                announcement_body = reduce(lambda body, member: body + f'{member}\n', new_members, announcement_body)
                announcement_body += '\n'

            if custom_message:
                announcement_body += f'{custom_message.content}\n\n'

            announcement_body += f'Happy Mapling, Go Grove! {emoji_id}'

            # Send announcement
            send_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
            announcement_message = await send_channel.send(announcement_body)
            await announcement_message.add_reaction(emoji)

            # Create leaderboard thread and add link to main announcement
            leaderboard_thread_title = f'{sunday.year} Culvert & Flag Race Leaderboard - Week {leaderboard_week}'
            leaderboard_thread = await announcement_message.create_thread(name=leaderboard_thread_title)
            announcement_body = announcement_body.replace('LEADERBOARD_THREAD_ID_HERE', f'{leaderboard_thread.id}')
            print(announcement_body)
            await announcement_message.edit(content=announcement_body)

            # Send leaderboard ranking messages
            await announce_leaderboard(leaderboard_thread, leaderboard_thread_title, wp_list)

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

    buttonsView = Buttons()
    buttonsView.message = await interaction.followup.send(confirmation_message_body, view=buttonsView)


async def announce_leaderboard(leaderboard_thread, leaderboard_thread_title,
                               wp_list: list[sheets_members.WeeklyParticipation]):
    await leaderboard_thread.send(f'**{leaderboard_thread_title}**')
    leaderboard = get_leaderboard_output(wp_list)
    for line in leaderboard:
        await leaderboard_thread.send(line)
    await leaderboard_thread.send(
        f'*If you notice an error or have any questions or feedback, please let a <@&{config.GROVE_ROLE_ID_JUNIOR}> know. Thank you!*')


def get_leaderboard_output(wp_list: list[sheets_members.WeeklyParticipation]):
    output = []
    current_score = None
    line = ''
    for wp in wp_list:
        if wp.score != current_score:
            if current_score is not None:
                output.append(line)
            line = f'{wp.score} '
        line += f'{wp.discord_mention} '
        current_score = wp.score

    if current_score is not None:
        output.append(line)

    return output


def get_celestials(wp_list: list[sheets_members.WeeklyParticipation]):
    return list(filter(
        lambda wp: (wp.rank == sheets_members.ROLE_NAME_WARDEN
                    or wp.rank == sheets_members.ROLE_NAME_GUARDIAN
                    or wp.rank == sheets_members.ROLE_NAME_SPIRIT) and wp.ten_week_average >= sheets_members.AVERAGE_THRESHOLD_SPIRIT,
        wp_list))
