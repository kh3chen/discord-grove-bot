import asyncio
from datetime import datetime
from datetime import timedelta
from datetime import timezone
import itertools
from functools import reduce
from enum import Enum

import discord

import config
import sheets

SPREADSHEET_BOSS_PARTIES = config.SPREADSHEET_BOSS_PARTIES  # The ID of the boss parties spreadsheet
SHEET_BOSS_PARTIES_MEMBERS = config.SHEET_BOSS_PARTIES_MEMBERS  # The ID of the Members sheet
RANGE_BOSSES = 'Bosses!A2:D'
RANGE_PARTIES = 'Parties!A2:K'
RANGE_MEMBERS = 'Members!A2:C'

service = sheets.get_service()


class PartyStatus(Enum):
    open = 1
    full = 2
    exclusive = 3
    fill = 4
    retired = 5


class Weekday(Enum):
    mon = 1
    tue = 2
    wed = 3
    thu = 4
    fri = 5
    sat = 6
    sun = 7


SHEET_BOSSES_NAME = 0
SHEET_BOSSES_ROLE_COLOUR = 1
SHEET_BOSSES_HUMAN_READABLE = 2

SHEET_PARTIES_ROLE_ID = 0
SHEET_PARTIES_BOSS_NAME = 1
SHEET_PARTIES_PARTY_NUMBER = 2
SHEET_PARTIES_STATUS = 3
SHEET_PARTIES_MEMBER_COUNT = 4
SHEET_PARTIES_WEEKDAY = 5
SHEET_PARTIES_HOUR = 6
SHEET_PARTIES_MINUTE = 7
SHEET_PARTIES_THREAD_ID = 8
SHEET_PARTIES_MESSAGE_ID = 9
SHEET_PARTIES_BOSS_LIST_MESSAGE_ID = 10
SHEET_PARTIES_BOSS_LIST_DECORATOR_ID = 11

SHEET_MEMBERS_USER_ID = 0
SHEET_MEMBERS_PARTY_ROLE_ID = 1
SHEET_MEMBERS_JOB = 2

BOSS_PARTY_LIST_CHANNEL_ID = config.BOSS_PARTY_LIST_CHANNEL_ID


async def sync(ctx):
    bosses = __get_bosses()
    parties = __get_parties(ctx, bosses)

    __update_new_parties(parties)

    # Get list of members from sheet

    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_MEMBERS).execute()
    members_values = result.get('values', [])
    new_members_values = []
    print(f'Before:\n{members_values}')
    for party in parties:
        party_role_id = str(party.id)
        for member in party.members:
            member_user_id = str(member.id)
            try:
                next(members_value for members_value in members_values if
                     members_value[SHEET_MEMBERS_USER_ID] == member_user_id and members_value[
                         SHEET_MEMBERS_PARTY_ROLE_ID] == party_role_id)
            except StopIteration:  # Could not find
                new_members_values.append([member_user_id, party_role_id, ' '])
                continue

    print(f'New members:\n{new_members_values}')

    body = {
        'values': new_members_values
    }
    result = service.spreadsheets().values().append(spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_MEMBERS,
                                                    valueInputOption="RAW", body=body).execute()
    await ctx.send('Sync complete.')


async def add(ctx, member, party, job):
    # get list of bosses from sheet
    bosses = __get_bosses()

    # Validate that this is a boss party role
    if party.name.find(' ') != -1 and party.name[0:party.name.find(' ')] not in bosses.keys():
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
    body = {
        'values': [[str(member.id), str(party.id), job]]
    }
    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_MEMBERS,
        valueInputOption="RAW", body=body).execute()
    print(f"{(result.get('updates').get('updatedCells'))} cells appended.")
    print(body)

    # Add role to user
    await member.add_roles(party)

    # Update party data
    __update_existing_party(party)

    # Success
    await ctx.send(f'Successfully added {member.mention} {job} to {party.mention}.')


async def remove(ctx, member, party):
    bosses = __get_bosses()

    # Validate that this is a boss party role
    if party.name.find(' ') != -1 and party.name[0:party.name.find(' ')] not in bosses.keys():
        await ctx.send(f'Error - {party.mention} is not a boss party.')
        return

    # Check if the user is not in the party
    # Check if user has the role
    if member not in party.members:
        await ctx.send('Error - Member not in boss party.')
        return

    # Remove member from member sheet
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_MEMBERS).execute()
    members_values = result.get('values', [])

    delete_index = -1
    for members_value in members_values:
        if members_value[SHEET_MEMBERS_USER_ID] == str(member.id) and members_value[SHEET_MEMBERS_PARTY_ROLE_ID] == str(
                party.id):
            # Found the entry, remove it
            delete_index = members_values.index(members_value) + 1
            break

    if delete_index != -1:
        delete_body = {
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": SHEET_BOSS_PARTIES_MEMBERS,
                            "dimension": "ROWS",
                            "startIndex": delete_index,
                            "endIndex": delete_index + 1
                        }
                    }
                }
            ]
        }
        print(delete_body)
        result = service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_BOSS_PARTIES, body=delete_body).execute()

    # Remove role from user
    await member.remove_roles(party)

    # Update party data
    __update_existing_party(party)

    # Success
    await ctx.send(f'Successfully removed {member.mention} from {party.mention}.')


async def create(ctx, boss_name):
    # get list of bosses from sheet
    bosses = __get_bosses()

    if boss_name not in bosses.keys():
        await ctx.send(f'Error - `{boss_name}` is not a valid boss name. Valid boss names are as follows:\n'
                       f'`{reduce(lambda acc, val: acc + (", " if acc else "") + val, list(bosses.keys()))}`')
        return

    # - Now we create the role, set the colour, set the permissions
    # - Then we set the position

    parties = __get_parties(ctx, bosses)
    new_boss_party_index = list(bosses.keys()).index(boss_name)
    party_number = 1
    new_boss_party = None

    for party in parties:
        party_index = list(bosses.keys()).index(party.name[0:party.name.find(' ')])
        if boss_name in party.name:
            if 'Fill' in party.name:
                # Create party
                print(f'Before position = {party.position}')
                new_boss_party = await ctx.guild.create_role(name=f'{boss_name} Party {party_number}',
                                                             colour=int(bosses[boss_name][SHEET_BOSSES_ROLE_COLOUR],
                                                                        16), mentionable=True)
                print(f'After position = {party.position}')
                await new_boss_party.edit(position=party.position)
                parties.insert(parties.index(party), new_boss_party)
                break
            else:
                party_number += 1

        elif party_index > new_boss_party_index:
            new_boss_party = await ctx.guild.create_role(name=f'{boss_name} Party {party_number}',
                                                         colour=int(bosses[boss_name][SHEET_BOSSES_ROLE_COLOUR],
                                                                    16), mentionable=True)
            await new_boss_party.edit_role_positions(position=party.position)
            parties.insert(parties.index(party), new_boss_party)
            break

    if not new_boss_party:
        new_boss_party = await ctx.guild.create_role(name=f'{boss_name} Party {party_number}',
                                                     colour=int(bosses[boss_name][SHEET_BOSSES_ROLE_COLOUR],
                                                                16), mentionable=True)
        await new_boss_party.edit(position=parties[-1].position)
        parties.append(new_boss_party)

    # Update spreadsheet
    __update_new_parties(parties)

    await ctx.send(f'Successfully created {new_boss_party.mention}.')


async def set_time(ctx, party, weekday_str, hour, minute):
    weekday = Weekday[weekday_str]
    if not weekday:
        await ctx.send('Error - Invalid weekday. Valid input values: [ mon | tue | wed | thu | fri | sat | sun ]')
        return

    if hour < 0 or hour > 23:
        await ctx.send('Error - Invalid hour. Hour must be between 0-23.')
        return

    if minute < 0 or minute > 59:
        await ctx.send('Error - Invalid minute. Minute must be between 0-59.')
        return

    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_PARTIES).execute()
    parties_values = result.get('values', [])
    for parties_value in parties_values:
        if parties_value[SHEET_PARTIES_ROLE_ID] == str(party.id):
            parties_value[SHEET_PARTIES_WEEKDAY] = weekday.name
            parties_value[SHEET_PARTIES_HOUR] = hour
            parties_value[SHEET_PARTIES_MINUTE] = minute
            break

    body = {
        'values': parties_values
    }
    service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_PARTIES,
                                           valueInputOption="RAW", body=body).execute()

    message_content = f'Set <@&{party.id}> party time to {weekday.name} at +{hour}:{minute:02d}.\n'
    message_content += f'Next run: <t:{__get_next_scheduled_time(weekday.value, hour, minute)}:F>'
    await ctx.send(message_content)


async def retire(bot, ctx, party):
    bosses = __get_bosses()

    # Validate that this is a boss party role
    if party.name.find(' ') != -1 and party.name[0:party.name.find(' ')] not in bosses.keys():
        await ctx.send(f'Error - {party.mention} is not a boss party.')
        return

    if party.name.find('Retired') != -1:
        await ctx.send(f'Error - {party.mention} is already retired.')
        return

    # Confirmation
    confirmation_message_body = f'Are you sure you want to retire {party.mention}? The following {len(party.members)} member(s) will be removed from the party:\n'
    for member in party.members:
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
    for member in party.members:
        await remove(ctx, member, party)

    # Update party status to retired
    party = await party.edit(name=f'{party.name} (Retired)', mentionable=False)

    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_PARTIES).execute()
    parties_values = result.get('values', [])
    try:
        parties_value = next(
            value for value in parties_values if value[SHEET_PARTIES_ROLE_ID] == str(party.id))

        # Delete boss party list messages
        boss_party_list_channel = bot.get_channel(BOSS_PARTY_LIST_CHANNEL_ID)
        if parties_value[SHEET_PARTIES_BOSS_LIST_MESSAGE_ID].strip():
            message = await boss_party_list_channel.fetch_message(parties_value[SHEET_PARTIES_BOSS_LIST_MESSAGE_ID])
            await message.delete()
        if parties_value[SHEET_PARTIES_BOSS_LIST_DECORATOR_ID].strip():
            message = await boss_party_list_channel.fetch_message(parties_value[SHEET_PARTIES_BOSS_LIST_DECORATOR_ID])
            await message.delete()

        __update_existing_party(party)
        await ctx.send(f'{party.mention} has been retired.')

    except StopIteration:  # Could not find
        await ctx.send(f'Error - Unable to find the data for {party.mention} in the sheet.')
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

    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_PARTIES).execute()
    parties_values = result.get('values', [])

    await ctx.send('Deleting the existing boss party list...')
    await boss_party_list_channel.purge(limit=len(parties_values) * 2)

    for parties_value in parties_values:
        parties_value[SHEET_PARTIES_BOSS_LIST_MESSAGE_ID] = ' '
        parties_value[SHEET_PARTIES_BOSS_LIST_DECORATOR_ID] = ' '

    body = {
        'values': parties_values
    }
    service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_PARTIES,
                                           valueInputOption="RAW", body=body).execute()

    await ctx.send('Existing boss party list deleted.')

    # Build dict of party role IDs to their members
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_MEMBERS).execute()
    members_values = result.get('values', [])
    # Key of the following dictionaries is the boss party role ID
    parties_dict = {}
    members_dict = {}
    for parties_value in parties_values:
        parties_dict[parties_value[SHEET_PARTIES_ROLE_ID]] = parties_value
        members_dict[parties_value[SHEET_PARTIES_ROLE_ID]] = []

    for members_value in members_values:
        members_dict[members_value[SHEET_MEMBERS_PARTY_ROLE_ID]].append(members_value)

    # Send the boss party messages

    await ctx.send('Creating the new boss party list...')

    bosses = __get_bosses()
    current_boss = None
    for parties_value in parties_values:
        if parties_value[SHEET_PARTIES_STATUS] == PartyStatus.retired.name:
            continue

        # Send section title
        if not current_boss or current_boss[SHEET_BOSSES_NAME] != parties_value[SHEET_PARTIES_BOSS_NAME]:
            current_boss = bosses[parties_value[SHEET_PARTIES_BOSS_NAME]]
            section_title_content = f'_ _\n**{current_boss[SHEET_BOSSES_HUMAN_READABLE]}**\n_ _'
            message = await boss_party_list_channel.send(section_title_content)
            parties_value[SHEET_PARTIES_BOSS_LIST_DECORATOR_ID] = str(message.id)
        else:
            message = await boss_party_list_channel.send('_ _')
            parties_value[SHEET_PARTIES_BOSS_LIST_DECORATOR_ID] = str(message.id)

        message_content = f'<@&{parties_value[SHEET_PARTIES_ROLE_ID]}> <#THREAD_ID_HERE>\n*TIMESTAMP_HERE*\n'
        for members_value in members_dict[parties_value[SHEET_PARTIES_ROLE_ID]]:
            message_content += f'<@{members_value[SHEET_MEMBERS_USER_ID]}> {members_value[SHEET_MEMBERS_JOB]}\n'

        # Placeholder first to avoid mention
        message = await boss_party_list_channel.send(
            f'{parties_value[SHEET_PARTIES_BOSS_NAME]} Party {parties_value[SHEET_PARTIES_PARTY_NUMBER]}')
        await message.edit(content=message_content)
        parties_value[SHEET_PARTIES_BOSS_LIST_MESSAGE_ID] = str(message.id)

    body = {
        'values': parties_values
    }
    service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_PARTIES,
                                           valueInputOption="RAW", body=body).execute()

    await ctx.send('New boss party list complete.')


async def post_test(bot, ctx):
    test_forum_channel = bot.get_channel(config.TEST_CHANNEL_ID)
    test_thread_with_message = await test_forum_channel.create_thread(name="this is a test thread",
                                                                      content="this is the content")
    await ctx.send(f'made test thread <#{test_thread_with_message.thread.id}>')

    thread = test_forum_channel.get_thread(test_thread_with_message.thread.id)
    message = await thread.fetch_message(test_thread_with_message.message.id)

    await thread.edit(name='this is the edited name')
    await ctx.send(f'updated thread name')
    await message.edit(content='this is the edited message content')
    await ctx.send(f'updated message content')


def __get_bosses():
    # get list of bosses from sheet
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_BOSSES).execute()
    bosses_values = result.get('values', [])
    bosses = {}
    for bosses_value in bosses_values:
        bosses[bosses_value[0]] = bosses_value
    print(bosses)
    return bosses


def __get_parties(ctx, bosses):
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


def __update_new_parties(all_parties):
    # get list of parties from sheet
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_PARTIES).execute()
    parties_values = result.get('values', [])
    print(f'Before:\n{parties_values}')
    parties_values_index = 0
    for party in all_parties:
        role_id = str(party.id)
        boss_name_first_space = party.name.find(' ')
        boss_name = party.name[0:boss_name_first_space]
        party_number = str(
            party.name[boss_name_first_space + 1 + party.name[boss_name_first_space + 1:].find(' ') + 1:])
        if party.name.find('Retired') != -1:
            status = PartyStatus.retired.name
            party_number = party_number[0:party_number.find(' ')]  # Remove " (Retired)"
        elif party.name.find('Fill') != -1:
            status = PartyStatus.fill.name
        elif len(party.members) == 6:
            status = PartyStatus.full.name
        else:
            status = PartyStatus.open.name
        member_count = str(len(party.members))

        if parties_values_index == len(parties_values):
            # More party roles than in data
            parties_values.append([role_id, boss_name, party_number, status, member_count, ' ', ' ', ' '])
        elif parties_values[parties_values_index][SHEET_PARTIES_ROLE_ID] != role_id:
            # Party role doesn't match data, there must be a new record
            parties_values.insert(parties_values_index,
                                  [role_id, boss_name, party_number, status, member_count, ' ', ' ', ' '])
        else:  # Data exists
            pass

        parties_values_index += 1

    print(f'After:\n{parties_values}')

    body = {
        'values': parties_values
    }

    # Update parties

    result = service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_PARTIES,
                                                    valueInputOption="RAW", body=body).execute()


def __update_existing_party(party):
    # Update party in parties sheet if party will be full
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_BOSS_PARTIES,
                                                 range=RANGE_PARTIES).execute()
    parties_values = result.get('values', [])
    for parties_value in parties_values:
        if parties_value[SHEET_PARTIES_ROLE_ID] == str(party.id):  # The relevant party data
            parties_value[SHEET_PARTIES_MEMBER_COUNT] = str(len(party.members))
            if parties_value[SHEET_PARTIES_STATUS] == PartyStatus.open.name and len(party.members) == 6:
                # Update to full if it is open
                parties_value[SHEET_PARTIES_STATUS] = PartyStatus.full.name
            elif parties_value[SHEET_PARTIES_STATUS] == PartyStatus.full.name and len(party.members) < 6:
                # Update to open if it is full
                parties_value[SHEET_PARTIES_STATUS] = PartyStatus.open.name
            elif party.name.find('Retired') != -1:
                # Update to retired
                parties_value[SHEET_PARTIES_STATUS] = PartyStatus.retired.name
                parties_value[SHEET_PARTIES_BOSS_LIST_MESSAGE_ID] = ' '
                parties_value[SHEET_PARTIES_BOSS_LIST_DECORATOR_ID] = ' '
            break
    body = {
        'values': parties_values
    }
    service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_BOSS_PARTIES, range=RANGE_PARTIES,
                                           valueInputOption="RAW", body=body).execute()


def __get_next_scheduled_time(weekday: int, hour: int, minute: int):
    def unix_timestamp(dt: datetime):
        return int(datetime.timestamp(dt))

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
