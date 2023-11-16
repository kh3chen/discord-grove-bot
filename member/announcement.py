import datetime
from functools import reduce

import discord
from discord.ext import commands

import config
import member.sheets as sheets_members

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

            await interaction.followup.send(f'Sending the announcement in <#{ANNOUNCEMENT_CHANNEL_ID}>')

            # Validate the spreadsheet has a column for this week's announcement
            if not sheets_members.is_valid(guild_week, sunday.strftime('%Y-%m-%d')):
                await interaction.followup.send(
                    'Error - unable to find the member tracking data for this week\'s announcement. Announcement has been cancelled.')
                return

            # Create and format announcement message
            announcement_body = f'<@&{config.GROVE_ROLE_ID_GROVE}>\n\nThanks everyone for another great week of Grove! Here\'s our week {guild_week} recap:\n<#LEADERBOARD_THREAD_ID_HERE>\n\n'

            # Celestials
            celestial_role = bot.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_CELESTIAL)

            # Remove last week's Celestials
            for member in celestial_role.members:
                await member.remove_roles(bot.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_CELESTIAL))

            wp_list = sheets_members.get_weekly_participation()
            new_celestials = get_celestials(wp_list)

            for wp in new_celestials:
                member = bot.get_guild(config.GROVE_GUILD_ID).get_member(wp.discord_id)
                await member.add_roles(celestial_role)

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

            await interaction.followup.send("Done!")

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
        lambda wp: (wp.rank == 'Spirit' or wp.rank == 'Guardian' or wp.rank == 'Warden') and wp.ten_week_average >= 20,
        wp_list))
