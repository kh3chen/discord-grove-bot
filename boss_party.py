import asyncio
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from functools import reduce

import sheets_boss
import config

BOSS_PARTY_LIST_CHANNEL_ID = config.GROVE_CHANNEL_ID_BOSS_PARTY_LIST


async def sync(ctx):
    bosses_dict = sheets_boss.get_bosses_dict()
    discord_parties = __get_discord_parties(ctx, bosses_dict)

    __update_new_parties(discord_parties)

    # Get list of members from sheet

    sheets_members = sheets_boss.get_members_list()
    new_sheets_members = []
    print(f'Before:\n{sheets_members}')
    for party in discord_parties:
        party_role_id = str(party.id)
        for member in party.members:
            member_user_id = str(member.id)
            try:
                next(sheets_member for sheets_member in sheets_members if
                     sheets_member.user_id == member_user_id and sheets_member.party_role_id == party_role_id)
            except StopIteration:  # Could not find
                new_sheets_members.append(sheets_boss.SheetsMember([member_user_id, party_role_id, '']))
                continue

    print(f'New members:\n{new_sheets_members}')

    sheets_boss.append_members(new_sheets_members)
    await ctx.send('Sync complete.')


async def add(ctx, member, party, job):
    # get list of bosses from sheet
    bosses_dict = sheets_boss.get_bosses_dict()

    # Validate that this is a boss party role
    if party.name.find(' ') != -1 and party.name[0:party.name.find(' ')] not in bosses_dict.keys():
        await ctx.send(f'Error - {party.mention} is not a boss party.')
        return

    if party.name.find('Retired') != -1:
        await ctx.send(f'Error - {party.mention} is retired.')
        return

    # Check if the user is already in the party
    if member in party.members:
        await ctx.send(f'Error - {member.mention} is already in {party.mention}.')
        return

    # Check if the party is already full
    if len(party.members) == 6:
        await ctx.send(f'Error - {party.mention} is full.')
        return

    # Add member to member sheet
    sheets_boss.append_members([sheets_boss.SheetsMember([str(member.id), str(party.id), job])])

    # Add role to user
    await member.add_roles(party)

    # Update party data
    __update_existing_party(party)

    # Success
    await ctx.send(f'Successfully added {member.mention} {job} to {party.mention}.')


async def remove(ctx, member, discord_party):
    bosses_dict = sheets_boss.get_bosses_dict()

    # Validate that this is a boss party role
    if discord_party.name.find(' ') != -1 and discord_party.name[
                                              0:discord_party.name.find(' ')] not in bosses_dict.keys():
        await ctx.send(f'Error - {discord_party.mention} is not a boss party.')
        return

    # Check if the user is not in the party
    # Check if user has the role
    if member not in discord_party.members:
        await ctx.send('Error - Member not in boss party.')
        return

    # Remove member from member sheet
    sheets_members = sheets_boss.get_members_list()

    delete_index = -1
    for sheets_member in sheets_members:
        if sheets_member.user_id == str(member.id) and sheets_member.party_role_id == str(discord_party.id):
            # Found the entry, remove it
            delete_index = sheets_members.index(sheets_member) + 1
            break

    if delete_index != -1:
        sheets_boss.delete_member(delete_index)

    # Remove role from user
    await member.remove_roles(discord_party)

    # Update party data
    __update_existing_party(discord_party)

    # Success
    await ctx.send(f'Successfully removed {member.mention} from {discord_party.mention}.')


async def create(ctx, boss_name):
    # get list of bosses from sheet
    bosses_dict = sheets_boss.get_bosses_dict()

    if boss_name not in bosses_dict.keys():
        await ctx.send(f'Error - `{boss_name}` is not a valid boss name. Valid boss names are as follows:\n'
                       f'`{reduce(lambda acc, val: acc + (", " if acc else "") + val, list(bosses_dict.keys()))}`')
        return

    # - Now we create the role, set the colour, set the permissions
    # - Then we set the position

    parties = __get_discord_parties(ctx, bosses_dict)
    new_boss_party_index = list(bosses_dict.keys()).index(boss_name)
    party_number = 1
    new_boss_party = None

    for party in parties:
        party_index = list(bosses_dict.keys()).index(party.name[0:party.name.find(' ')])
        if boss_name in party.name:
            if 'Fill' in party.name:
                # Create party
                print(f'Before position = {party.position}')
                new_boss_party = await ctx.guild.create_role(name=f'{boss_name} Party {party_number}',
                                                             colour=bosses_dict[boss_name].get_role_colour(),
                                                             mentionable=True)
                print(f'After position = {party.position}')
                await new_boss_party.edit(position=party.position)
                parties.insert(parties.index(party), new_boss_party)
                break
            else:
                party_number += 1

        elif party_index > new_boss_party_index:
            new_boss_party = await ctx.guild.create_role(name=f'{boss_name} Party {party_number}',
                                                         colour=bosses_dict[boss_name].get_role_colour(),
                                                         mentionable=True)
            await new_boss_party.edit_role_positions(position=party.position)
            parties.insert(parties.index(party), new_boss_party)
            break

    if not new_boss_party:
        new_boss_party = await ctx.guild.create_role(name=f'{boss_name} Party {party_number}',
                                                     colour=bosses_dict[boss_name].get_role_colour(),
                                                     mentionable=True)
        await new_boss_party.edit(position=parties[-1].position)
        parties.append(new_boss_party)

    # Update spreadsheet
    __update_new_parties(parties)

    await ctx.send(f'Successfully created {new_boss_party.mention}.')


async def set_time(bot, ctx, discord_party, weekday_str, hour, minute):
    weekday = sheets_boss.SheetsParty.Weekday[weekday_str]
    if not weekday:
        await ctx.send('Error - Invalid weekday. Valid input values: [ mon | tue | wed | thu | fri | sat | sun ]')
        return

    if hour < 0 or hour > 23:
        await ctx.send('Error - Invalid hour. Hour must be from 0-23.')
        return

    if minute < 0 or minute > 59:
        await ctx.send('Error - Invalid minute. Minute must be from 0-59.')
        return

    sheets_parties = sheets_boss.get_parties_list()
    try:
        sheets_party = next(
            sheets_party for sheets_party in sheets_parties if sheets_party.role_id == str(discord_party.id))
        sheets_party.weekday = weekday.name
        sheets_party.hour = str(hour)
        sheets_party.minute = str(minute)
    except StopIteration:
        await ctx.send(f'Error - Unable to find party {discord_party.id} in the boss parties data.')
        return

    sheets_boss.update_parties(sheets_parties)

    next_run_timestamp = __get_next_scheduled_time(weekday.value, hour, minute)

    message_content = f'Set <@&{sheets_party.role_id}> party time to {weekday.name} at +{hour}:{minute:02d}.\n'
    message_content += f'Next run: <t:{next_run_timestamp}:F>'
    await ctx.send(message_content)

    if sheets_party.boss_list_message_id:
        # Update boss list message
        await ctx.send(f'Updating the timestamp in the <#{BOSS_PARTY_LIST_CHANNEL_ID}> message...')

        # Key of the following dictionaries is the boss party role ID
        party_sheets_members = []
        sheets_members = sheets_boss.get_members_list()

        for sheets_member in sheets_members:
            if sheets_member.party_role_id == sheets_party.role_id:
                party_sheets_members.append(sheets_member)

        boss_party_list_channel = bot.get_channel(BOSS_PARTY_LIST_CHANNEL_ID)
        message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
        await __update_boss_party_list_message(message, str(sheets_party.role_id), sheets_party.party_thread_id,
                                               next_run_timestamp,
                                               party_sheets_members)

        await ctx.send(
            content=f'Boss party list message updated:\n{config.DISCORD_CHANNELS_URL_PREFIX}{config.GROVE_GUILD_ID}/{BOSS_PARTY_LIST_CHANNEL_ID}/{message.id}.',
            suppress_embeds=True)


async def retire(bot, ctx, discord_party):
    bosses_dict = sheets_boss.get_bosses_dict()

    # Validate that this is a boss party role
    if discord_party.name.find(' ') != -1 and discord_party.name[
                                              0:discord_party.name.find(' ')] not in bosses_dict.keys():
        await ctx.send(f'Error - {discord_party.mention} is not a boss party.')
        return

    if discord_party.name.find('Retired') != -1:
        await ctx.send(f'Error - {discord_party.mention} is already retired.')
        return

    # Confirmation
    confirmation_message_body = f'Are you sure you want to retire {discord_party.mention}? The following {len(discord_party.members)} member(s) will be removed from the party:\n'
    for member in discord_party.members:
        confirmation_message_body += f'{member.mention}\n'
    confirmation_message_body += f'\nReact with 👍 to proceed.'

    confirmation_message = await ctx.send(confirmation_message_body)
    await confirmation_message.add_reaction('👍')

    def check(reaction, user):
        print(reaction)
        return user == ctx.author and str(reaction.emoji) == '👍'

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send('Error - confirmation expired. Party retire has been cancelled.')
        return

    # Remove members from party
    for member in discord_party.members:
        await remove(ctx, member, discord_party)

    # Update party status to retired
    discord_party = await discord_party.edit(name=f'{discord_party.name} (Retired)', mentionable=False)
    sheets_parties = sheets_boss.get_parties_list()
    try:
        parties_value = next(
            parties_value for parties_value in sheets_parties if parties_value.role_id == str(discord_party.id))

        # Delete boss party list messages
        boss_party_list_channel = bot.get_channel(BOSS_PARTY_LIST_CHANNEL_ID)
        if parties_value.boss_list_message_id:
            message = await boss_party_list_channel.fetch_message(parties_value.boss_list_message_id)
            await message.delete()
        if parties_value.boss_list_decorator_id:
            message = await boss_party_list_channel.fetch_message(parties_value.boss_list_decorator_id)
            await message.delete()

        __update_existing_party(discord_party)
        await ctx.send(f'{discord_party.mention} has been retired.')

    except StopIteration:  # Could not find
        await ctx.send(f'Error - Unable to find the data for {discord_party.mention} in the sheet.')
        return


async def list_remake(bot, ctx):
    # Confirmation
    confirmation_message_body = f'Are you sure you want to remake the boss party list in <#{BOSS_PARTY_LIST_CHANNEL_ID}>?\n'
    confirmation_message_body += f'\nReact with 👍 to proceed.'

    confirmation_message = await ctx.send(confirmation_message_body)
    await confirmation_message.add_reaction('👍')

    def check(reaction, user):
        print(reaction)
        return user == ctx.author and str(reaction.emoji) == '👍'

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send('Error - confirmation expired. Party retire has been cancelled.')
        return

    # Delete existing messages
    boss_party_list_channel = bot.get_channel(BOSS_PARTY_LIST_CHANNEL_ID)

    sheets_parties = sheets_boss.get_parties_list()

    await ctx.send('Deleting the existing boss party list...')
    await boss_party_list_channel.purge(limit=len(sheets_parties) * 2)

    try:
        for sheets_party in sheets_parties:
            print(sheets_party)
            sheets_party.boss_list_message_id = ''
            sheets_party.boss_list_decorator_id = ''
    except IndexError:
        return

    sheets_boss.update_parties(sheets_parties)

    await ctx.send('Existing boss party list deleted.')

    # Build dict of party role IDs to their members
    sheets_members = sheets_boss.get_members_list()
    # Key of the following dictionaries is the boss party role ID
    members_dict = {}
    for sheets_party in sheets_parties:
        members_dict[sheets_party.role_id] = []

    for sheets_member in sheets_members:
        members_dict[sheets_member.party_role_id].append(sheets_member)

    # Send the boss party messages

    await ctx.send('Creating the new boss party list...')

    bosses_dict = sheets_boss.get_bosses_dict()
    current_sheets_boss = None
    for sheets_party in sheets_parties:
        if sheets_party.status == sheets_boss.SheetsParty.PartyStatus.retired.name:
            continue

        # Send section title
        if not current_sheets_boss or current_sheets_boss.boss_name != sheets_party.boss_name:
            current_sheets_boss = bosses_dict[sheets_party.boss_name]
            section_title_content = f'_ _\n**{current_sheets_boss.human_readable_name}**\n_ _'
            message = await boss_party_list_channel.send(section_title_content)
            sheets_party.boss_list_decorator_id = str(message.id)
        else:
            message = await boss_party_list_channel.send('_ _')
            sheets_party.boss_list_decorator_id = str(message.id)

        message_content = f'<@&{sheets_party.role_id}> <#THREAD_ID_HERE>\n*TIMESTAMP_HERE*\n'
        for sheets_member in members_dict[sheets_party.role_id]:
            message_content += f'<@{sheets_member.user_id}> {sheets_member.job}\n'

        # Placeholder first to avoid mention
        message = await boss_party_list_channel.send(
            f'{sheets_party.boss_name} Party {sheets_party.party_number}')
        sheets_party.boss_list_message_id = str(message.id)

        await __update_boss_party_list_message(message, sheets_party.role_id,
                                               sheets_party.party_thread_id, sheets_party.get_next_scheduled_time(),
                                               members_dict[sheets_party.role_id])

    sheets_boss.update_parties(sheets_parties)

    await ctx.send('New boss party list complete.')


async def post_test(bot, ctx):
    test_forum_channel = bot.get_channel(config.GROVE_CHANNEL_ID_TEST)
    test_thread_with_message = await test_forum_channel.create_thread(name="this is a test thread",
                                                                      content="this is the content")
    await ctx.send(f'made test thread <#{test_thread_with_message.thread.id}>')

    thread = test_forum_channel.get_thread(test_thread_with_message.thread.id)
    message = await thread.fetch_message(test_thread_with_message.message.id)

    await thread.edit(name='this is the edited name')
    await ctx.send(f'updated thread name')
    await message.edit(content='this is the edited message content')
    await ctx.send(f'updated message content')


def __get_discord_parties(ctx, bosses):
    """Returns the cached [discord.Role] from Discord context. Any recent changes made to roles may not be reflected in the response."""
    # get all boss party roles by matching their names to the bosses
    parties = []
    for role in ctx.guild.roles:
        if role.name.find(' ') == -1 or role.name.find('Practice') != -1:
            continue

        if role.name[0:role.name.find(' ')] in bosses.keys():
            parties.append(role)

    parties.reverse()  # Roles are ordered bottom up
    print(parties)
    return parties


def __update_new_parties(discord_parties):
    # get list of parties from sheet
    sheets_parties = sheets_boss.get_parties_list()
    print(f'Before:\n{sheets_parties}')
    parties_values_index = 0
    for discord_party in discord_parties:
        new_sheets_party = sheets_boss.SheetsParty([])
        # TODO: Refactor to allow `sheets.SheetsParty(discord.Role)` where role is validated as a boss party
        new_sheets_party.role_id = str(discord_party.id)
        boss_name_first_space = discord_party.name.find(' ')
        new_sheets_party.boss_name = discord_party.name[0:boss_name_first_space]
        new_sheets_party.party_number = str(
            discord_party.name[boss_name_first_space + 1
                               + discord_party.name[boss_name_first_space + 1:].find(' ') + 1:])
        if discord_party.name.find('Retired') != -1:
            new_sheets_party.status = sheets_boss.SheetsParty.PartyStatus.retired.name
            new_sheets_party.party_number = new_sheets_party.party_number[
                                            0:new_sheets_party.party_number.find(' ')]  # Remove " (Retired)"
        elif discord_party.name.find('Fill') != -1:
            new_sheets_party.status = sheets_boss.SheetsParty.PartyStatus.fill.name
        elif len(discord_party.members) == 6:
            new_sheets_party.status = sheets_boss.SheetsParty.PartyStatus.full.name
        else:
            new_sheets_party.status = sheets_boss.SheetsParty.PartyStatus.open.name
        new_sheets_party.member_count = str(len(discord_party.members))

        print(parties_values_index)
        if parties_values_index == len(sheets_parties):
            # More party roles than in data
            sheets_parties.append(new_sheets_party)
        elif sheets_parties[parties_values_index].role_id != new_sheets_party.role_id:
            # Party role doesn't match data, there must be a new record
            sheets_parties.insert(parties_values_index, new_sheets_party)
        else:  # Data exists
            pass

        parties_values_index += 1

    print(f'After:\n{sheets_parties}')

    # Update parties
    sheets_boss.update_parties(sheets_parties)


def __update_existing_party(party):
    # Update party status and member count
    sheets_parties = sheets_boss.get_parties_list()
    for sheets_party in sheets_parties:
        if sheets_party.role_id == str(party.id):  # The relevant party data
            sheets_party.member_count = str(len(party.members))
            if sheets_party.status == sheets_boss.SheetsParty.PartyStatus.open.name and len(party.members) == 6:
                # Update to full if it is open
                sheets_party.status = sheets_boss.SheetsParty.PartyStatus.full.name
            elif sheets_party.status == sheets_boss.SheetsParty.PartyStatus.full.name and len(party.members) < 6:
                # Update to open if it is full
                sheets_party.status = sheets_boss.SheetsParty.PartyStatus.open.name
            elif party.name.find('Retired') != -1:
                # Update to retired
                sheets_party.status = sheets_boss.SheetsParty.PartyStatus.retired.name
                sheets_party.boss_list_message_id = ''
                sheets_party.boss_list_decorator_id = ''
            break

    sheets_boss.update_parties(sheets_parties)


async def __update_boss_party_list_message(message, party_id: str, thread_id: str, timestamp: str,
                                           sheets_members: list[sheets_boss.SheetsMember]):
    message_content = f'<@&{party_id}>'
    if thread_id:
        message_content += f'<#{thread_id}>'
    message_content += '\n'
    if timestamp:
        message_content += f'**Next run:** <t:{timestamp}:F> <t:{timestamp}:R>\n'
    for sheets_member in sheets_members:
        message_content += f'<@{sheets_member.user_id}> {sheets_member.job}\n'
    await message.edit(content=message_content)


def __get_next_scheduled_time(weekday: int, hour: int, minute: int):
    def unix_timestamp(dt: datetime):
        return str(int(datetime.timestamp(dt)))

    now = datetime.now(timezone.utc)
    if now.isoweekday() == weekday:
        if now.hour > hour or now.hour == hour and now.minute > minute:
            next_time = (now + timedelta(days=7)).replace(hour=hour, minute=minute)
            return unix_timestamp(next_time)
        else:
            next_time = now.replace(hour=hour, minute=minute)
            return unix_timestamp(next_time)
    else:
        next_time = (now + timedelta(days=(weekday - now.isoweekday()) % 7)).replace(hour=hour, minute=minute)
        return unix_timestamp(next_time)
