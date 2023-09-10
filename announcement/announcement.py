import asyncio
import datetime
from functools import reduce

import config
import announcement.sheets as sheets_members

GUILD_CREATED_ON = datetime.date(2021, 12, 19)
ANNOUNCEMENT_CHANNEL_ID = config.GROVE_CHANNEL_ID_ANNOUNCEMENTS


async def send_announcement(bot, ctx, emoji_id: str, custom_message_id: str):
    today = datetime.date.today()
    sunday = today - datetime.timedelta(days=(today.weekday() + 1) % 7)
    guild_week = (sunday - GUILD_CREATED_ON).days // 7
    leaderboard_week = sunday.strftime('%U')

    # Confirmation
    try:
        emoji = next(e for e in bot.emojis if str(e) == emoji_id)
    except StopIteration:
        await ctx.send('Error - invalid emoji, please use an emoji from this server. Announcement has been cancelled.')
        return

    custom_message = None
    if custom_message_id:
        custom_message = await ctx.fetch_message(custom_message_id)

    confirmation_message_body = f'Are you sure you want to send the announcement?\n\nWeek {guild_week}\n{sunday}\n{sunday.year} Leaderboard Week {leaderboard_week}\n\n'
    if custom_message:
        confirmation_message_body += f'Custom message:\n```{custom_message.content}```\n\n'
    confirmation_message_body += f'React with {emoji_id} to proceed.'

    confirmation_message = await ctx.send(confirmation_message_body)
    await confirmation_message.add_reaction(emoji)

    def check(reaction, user):
        print(reaction)
        return user == ctx.author and str(reaction.emoji) == emoji_id

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send('Error - confirmation expired. Announcement has been cancelled.')
        return
    else:
        await ctx.send(f'Sending the announcement in <#{ANNOUNCEMENT_CHANNEL_ID}>')

    # Defer because sending the announcement takes longer than 3 seconds
    # await ctx.defer()

    # Validate the spreadsheet has a column for this week's announcement
    if not sheets_members.is_valid(guild_week, sunday.strftime('%Y-%m-%d')):
        await ctx.send(
            'Error - unable to find the member tracking data for this week\'s announcement. Announcement has been cancelled.')
        return

    # Create and format announcement message
    announcement_body = f'<@&{config.GROVE_ROLE_ID_GROVE}>\n\nThanks everyone for another great week of Grove! Here\'s our week {guild_week} recap:\n<#LEADERBOARD_THREAD_ID_HERE>\n\n'

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
    await announce_leaderboard(leaderboard_thread, leaderboard_thread_title)

    await ctx.reply("Done!")


async def announce_leaderboard(leaderboard_thread, leaderboard_thread_title):
    await leaderboard_thread.send(f'**{leaderboard_thread_title}**')
    leaderboard = sheets_members.get_leaderboard()
    for line in leaderboard:
        await leaderboard_thread.send(line)
    await leaderboard_thread.send(
        f'*If you notice an error or have any questions or feedback, please let a <@&{config.GROVE_ROLE_ID_JUNIOR}> know. Thank you!*')
