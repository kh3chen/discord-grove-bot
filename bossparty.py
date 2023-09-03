import asyncio
from functools import reduce

from sheets_bossing import SheetsBossing
from sheets_bossing import Party as SheetsParty
from sheets_bossing import Member as SheetsMember
import config

BOSS_PARTY_LIST_CHANNEL_ID = config.GROVE_CHANNEL_ID_BOSS_PARTY_LIST

sheets_bossing = SheetsBossing()


async def sync(ctx):
    discord_parties = __get_discord_parties(ctx, sheets_bossing.get_boss_names())

    # Update parties data
    __update_with_new_parties(discord_parties)

    # Update members data
    new_sheets_members = []
    for discord_party in discord_parties:
        party_role_id = str(discord_party.id)
        boss_name_first_space = discord_party.name.find(' ')
        boss_name = discord_party.name[0:boss_name_first_space]
        party_number = str(
            discord_party.name[boss_name_first_space + 1
                               + discord_party.name[boss_name_first_space + 1:].find(' ') + 1:])
        for member in discord_party.members:
            member_user_id = str(member.id)
            try:
                next(sheets_member for sheets_member in sheets_bossing.members if
                     sheets_member.user_id == member_user_id and sheets_member.party_role_id == party_role_id)
            except StopIteration:
                # New member
                new_sheets_members.append(SheetsMember(
                    boss_name=boss_name,
                    party_number=party_number,
                    party_role_id=party_role_id,
                    user_id=member_user_id,
                    job=''))
                continue

    print(f'New members:\n{new_sheets_members}')

    sheets_bossing.append_members(new_sheets_members)
    await ctx.send('Sync complete.')


async def add(bot, ctx, member, discord_party, job):
    # Validate that this is a boss party role
    try:
        sheets_party = next(
            sheets_party for sheets_party in sheets_bossing.parties if
            sheets_party.role_id == str(discord_party.id))
    except StopIteration:
        await ctx.send(f'Error - Unable to find party {discord_party.id} in the boss parties data.')
        return

    if sheets_party.status == SheetsParty.PartyStatus.retired:
        await ctx.send(f'Error - {discord_party.mention} is retired.')
        return

    # Check if the party is already full
    if sheets_party.status == SheetsParty.PartyStatus.full or len(discord_party.members) == 6:
        await ctx.send(f'Error - {discord_party.mention} is full.')
        return

    # Check if the user is already in the party
    if member in discord_party.members:
        await ctx.send(f'Error - {member.mention} is already in {discord_party.mention}.')
        return

    # Add member to member sheet
    sheets_bossing.append_members([SheetsMember(boss_name=sheets_party.boss_name,
                                                party_number=sheets_party.party_number,
                                                party_role_id=sheets_party.role_id,
                                                user_id=str(member.id),
                                                job=job)])

    # Add role to user
    await member.add_roles(discord_party)

    # Update party data
    __update_existing_party(discord_party)

    # Success
    await ctx.send(f'Successfully added {member.mention} {job} to {discord_party.mention}.')

    if sheets_party.boss_list_message_id:
        # Update boss list message

        boss_party_list_channel = bot.get_channel(BOSS_PARTY_LIST_CHANNEL_ID)
        message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
        await __update_boss_party_list_message(message, sheets_party)

        await ctx.send(
            content=f'Boss party list message updated:\n{config.DISCORD_CHANNELS_URL_PREFIX}{config.GROVE_GUILD_ID}/{BOSS_PARTY_LIST_CHANNEL_ID}/{message.id}.',
            ephemeral=True,
            suppress_embeds=True)


async def remove(bot, ctx, member, discord_party):
    # Validate that this is a boss party role
    try:
        sheets_party = next(
            sheets_party for sheets_party in sheets_bossing.parties if
            sheets_party.role_id == str(discord_party.id))
    except StopIteration:
        await ctx.send(f'Error - Unable to find party {discord_party.id} in the boss parties data.')
        return

    # Check if user has the role
    if member not in discord_party.members:
        await ctx.send('Error - Member not in boss party.')
        return

    # Remove member from member sheet
    sheets_bossing.delete_member(SheetsMember(boss_name=sheets_party.boss_name,
                                              party_number=sheets_party.party_number,
                                              party_role_id=sheets_party.role_id,
                                              user_id=str(member.id)))

    # Remove role from user
    await member.remove_roles(discord_party)

    # Update party data
    __update_existing_party(discord_party)

    # Success
    await ctx.send(f'Successfully removed {member.mention} from {discord_party.mention}.')

    if sheets_party.boss_list_message_id:
        # Update boss list message

        boss_party_list_channel = bot.get_channel(BOSS_PARTY_LIST_CHANNEL_ID)
        message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
        await __update_boss_party_list_message(message, sheets_party)

        await ctx.send(
            content=f'Boss party list message updated:\n{config.DISCORD_CHANNELS_URL_PREFIX}{config.GROVE_GUILD_ID}/{BOSS_PARTY_LIST_CHANNEL_ID}/{message.id}.',
            ephemeral=True,
            suppress_embeds=True)


async def create(bot, ctx, boss_name):
    # get list of bosses from sheet
    bosses_dict = sheets_bossing.bosses_dict

    if boss_name not in sheets_bossing.get_boss_names():
        await ctx.send(f'Error - `{boss_name}` is not a valid boss name. Valid boss names are as follows:\n'
                       f'`{reduce(lambda acc, val: acc + (", " if acc else "") + val, sheets_bossing.get_boss_names())}`')
        return

    # - Now we create the role, set the colour, set the permissions
    # - Then we set the position

    discord_parties = __get_discord_parties(ctx, sheets_bossing.get_boss_names())
    new_party_boss_index = sheets_bossing.get_boss_names().index(boss_name)
    party_number = 1
    new_boss_party = None

    for discord_party in discord_parties:
        party_boss_index = sheets_bossing.get_boss_names().index(discord_party.name[0:discord_party.name.find(' ')])
        if boss_name in discord_party.name:
            if 'Fill' in discord_party.name:
                # Create party
                print(f'Before position = {discord_party.position}')
                new_boss_party = await ctx.guild.create_role(name=f'{boss_name} Party {party_number}',
                                                             colour=sheets_bossing.bosses_dict[
                                                                 boss_name].get_role_colour(),
                                                             mentionable=True)
                print(f'After position = {discord_party.position}')
                await new_boss_party.edit(position=discord_party.position)
                discord_parties.insert(discord_parties.index(discord_party), new_boss_party)
                break
            else:
                party_number += 1

        elif party_boss_index > new_party_boss_index:
            new_boss_party = await ctx.guild.create_role(name=f'{boss_name} Party {party_number}',
                                                         colour=sheets_bossing.bosses_dict[boss_name].get_role_colour(),
                                                         mentionable=True)
            await new_boss_party.edit_role_positions(position=discord_party.position)
            discord_parties.insert(discord_parties.index(discord_party), new_boss_party)
            break

    if not new_boss_party:
        new_boss_party = await ctx.guild.create_role(name=f'{boss_name} Party {party_number}',
                                                     colour=sheets_bossing.bosses_dict[boss_name].get_role_colour(),
                                                     mentionable=True)
        await new_boss_party.edit(position=discord_parties[-1].position)
        discord_parties.append(new_boss_party)

    # Update spreadsheet
    __update_with_new_parties(discord_parties)

    await ctx.send(f'Successfully created {new_boss_party.mention}.')

    # Remake boss party list
    await remake_boss_party_list(bot, ctx)


async def settime(bot, ctx, discord_party, weekday_str, hour, minute):
    weekday = SheetsParty.Weekday[weekday_str]
    if not weekday:
        await ctx.send('Error - Invalid weekday. Valid input values: [ mon | tue | wed | thu | fri | sat | sun ]')
        return

    if hour < 0 or hour > 23:
        await ctx.send('Error - Invalid hour. Hour must be from 0-23.')
        return

    if minute < 0 or minute > 59:
        await ctx.send('Error - Invalid minute. Minute must be from 0-59.')
        return

    sheets_parties = sheets_bossing.parties
    try:
        sheets_party = next(
            sheets_party for sheets_party in sheets_parties if sheets_party.role_id == str(discord_party.id))
    except StopIteration:
        await ctx.send(f'Error - Unable to find party {discord_party.id} in the boss parties data.')
        return

    sheets_party.weekday = weekday.name
    sheets_party.hour = str(hour)
    sheets_party.minute = str(minute)
    sheets_bossing.update_parties(sheets_parties)

    message_content = f'Set <@&{sheets_party.role_id}> party time to {weekday.name} at +{hour}:{minute:02d}.\n'
    message_content += f'Next run: <t:{sheets_party.next_scheduled_time()}:F>'
    await ctx.send(message_content)

    if sheets_party.boss_list_message_id:
        # Update boss list message

        boss_party_list_channel = bot.get_channel(BOSS_PARTY_LIST_CHANNEL_ID)
        message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
        await __update_boss_party_list_message(message, sheets_party)

        await ctx.send(
            content=f'Boss party list message updated:\n{config.DISCORD_CHANNELS_URL_PREFIX}{config.GROVE_GUILD_ID}/{BOSS_PARTY_LIST_CHANNEL_ID}/{message.id}.',
            ephemeral=True,
            suppress_embeds=True)


async def retire(bot, ctx, discord_party):
    # Validate that this is a boss party role
    if discord_party.name.find(' ') != -1 and discord_party.name[
                                              0:discord_party.name.find(' ')] not in sheets_bossing.get_boss_names():
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
        await remove(bot, ctx, member, discord_party)

    # Update party status to retired
    discord_party = await discord_party.edit(name=f'{discord_party.name} (Retired)', mentionable=False)
    try:
        sheets_party = next(
            sheets_party for sheets_party in sheets_bossing.parties if sheets_party.role_id == str(discord_party.id))

        # Delete boss party list messages
        boss_party_list_channel = bot.get_channel(BOSS_PARTY_LIST_CHANNEL_ID)
        if sheets_party.boss_list_message_id:
            message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
            await message.delete()
        if sheets_party.boss_list_decorator_id:
            message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_decorator_id)
            await message.delete()

        __update_existing_party(discord_party)
        await ctx.send(f'{discord_party.mention} has been retired.')

    except StopIteration:  # Could not find
        await ctx.send(f'Error - Unable to find the data for {discord_party.mention} in the sheet.')
        return


async def exclusive(bot, ctx, discord_party):
    new_sheets_parties = sheets_bossing.parties
    try:
        sheets_party = next(
            sheets_party for sheets_party in new_sheets_parties if sheets_party.role_id == str(discord_party.id))
    except StopIteration:
        await ctx.send(f'Error - Unable to find party {discord_party.id} in the boss parties data.')
        return

    sheets_party.status = SheetsParty.PartyStatus.exclusive.name
    sheets_bossing.update_parties(new_sheets_parties)

    await ctx.send(f'<@&{sheets_party.role_id}> is now exclusive.')

    if sheets_party.boss_list_message_id:
        # Update boss list message

        boss_party_list_channel = bot.get_channel(BOSS_PARTY_LIST_CHANNEL_ID)
        message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
        await __update_boss_party_list_message(message, sheets_party)

        await ctx.send(
            content=f'Boss party list message updated:\n{config.DISCORD_CHANNELS_URL_PREFIX}{config.GROVE_GUILD_ID}/{BOSS_PARTY_LIST_CHANNEL_ID}/{message.id}.',
            ephemeral=True,
            suppress_embeds=True)


async def open(bot, ctx, discord_party):
    new_sheets_parties = sheets_bossing.parties
    try:
        sheets_party = next(
            sheets_party for sheets_party in new_sheets_parties if sheets_party.role_id == str(discord_party.id))
    except StopIteration:
        await ctx.send(f'Error - Unable to find party {discord_party.id} in the boss parties data.')
        return

    message_content = f'<@&{sheets_party.role_id}> is now open.'
    if len(discord_party.members) == 6:
        message_content += " (Full)"
        sheets_party.status = SheetsParty.PartyStatus.full.name
    else:
        sheets_party.status = SheetsParty.PartyStatus.open.name
    sheets_bossing.update_parties(new_sheets_parties)

    await ctx.send(message_content)

    if sheets_party.boss_list_message_id:
        # Update boss list message

        boss_party_list_channel = bot.get_channel(BOSS_PARTY_LIST_CHANNEL_ID)
        message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
        await __update_boss_party_list_message(message, sheets_party)

        await ctx.send(
            content=f'Boss party list message updated:\n{config.DISCORD_CHANNELS_URL_PREFIX}{config.GROVE_GUILD_ID}/{BOSS_PARTY_LIST_CHANNEL_ID}/{message.id}.',
            ephemeral=True,
            suppress_embeds=True)


async def listremake(bot, ctx):
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

    await remake_boss_party_list(bot, ctx)


async def remake_boss_party_list(bot, ctx):
    # Delete existing messages
    boss_party_list_channel = bot.get_channel(BOSS_PARTY_LIST_CHANNEL_ID)

    new_sheets_parties = sheets_bossing.parties

    await ctx.send('Deleting the existing boss party list...')
    await boss_party_list_channel.purge(limit=len(new_sheets_parties) * 2)

    try:
        for sheets_party in new_sheets_parties:
            sheets_party.boss_list_message_id = ''
            sheets_party.boss_list_decorator_id = ''
    except IndexError:
        return

    sheets_bossing.update_parties(new_sheets_parties)

    await ctx.send('Existing boss party list deleted.')

    # Send the boss party messages
    await ctx.send('Creating the new boss party list...')

    members_dict = sheets_bossing.get_members_dict()
    bosses_dict = sheets_bossing.bosses_dict
    current_sheets_boss = None
    for sheets_party in new_sheets_parties:
        if sheets_party.status == SheetsParty.PartyStatus.retired.name:
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

        await __update_boss_party_list_message(message, sheets_party, members_dict[sheets_party.role_id])

    sheets_bossing.update_parties(new_sheets_parties)

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


def __get_discord_parties(ctx, boss_names):
    """Returns the cached [discord.Role] from Discord context. Any recent changes made to roles may not be reflected in the response."""
    # get all boss party roles by matching their names to the bosses
    parties = []
    for role in ctx.guild.roles:
        if role.name.find(' ') == -1 or role.name.find('Practice') != -1:
            continue

        if role.name[0:role.name.find(' ')] in boss_names:
            parties.append(role)

    parties.reverse()  # Roles are ordered bottom up
    print(parties)
    return parties


def __update_with_new_parties(discord_parties):
    # get list of parties from sheet
    new_sheets_parties = sheets_bossing.parties
    print(f'Before:\n{new_sheets_parties}')
    parties_values_index = 0
    for discord_party in discord_parties:
        new_sheets_party = SheetsParty.from_sheets_value([])
        new_sheets_party.role_id = str(discord_party.id)
        boss_name_first_space = discord_party.name.find(' ')
        new_sheets_party.boss_name = discord_party.name[0:boss_name_first_space]
        new_sheets_party.party_number = str(
            discord_party.name[boss_name_first_space + 1
                               + discord_party.name[boss_name_first_space + 1:].find(' ') + 1:])
        if discord_party.name.find('Retired') != -1:
            new_sheets_party.status = SheetsParty.PartyStatus.retired.name
            new_sheets_party.party_number = new_sheets_party.party_number[
                                            0:new_sheets_party.party_number.find(' ')]  # Remove " (Retired)"
        elif discord_party.name.find('Fill') != -1:
            new_sheets_party.status = SheetsParty.PartyStatus.fill.name
        elif len(discord_party.members) == 6:
            new_sheets_party.status = SheetsParty.PartyStatus.full.name
        elif len(discord_party.members) == 0:
            new_sheets_party.status = SheetsParty.PartyStatus.new.name
        else:
            new_sheets_party.status = SheetsParty.PartyStatus.open.name
        new_sheets_party.member_count = str(len(discord_party.members))

        print(parties_values_index)
        if parties_values_index == len(new_sheets_parties):
            # More party roles than in data
            new_sheets_parties.append(new_sheets_party)
        elif new_sheets_parties[parties_values_index].role_id != new_sheets_party.role_id:
            # Party role doesn't match data, there must be a new record
            new_sheets_parties.insert(parties_values_index, new_sheets_party)
        else:  # Data exists
            pass

        parties_values_index += 1

    print(f'After:\n{new_sheets_parties}')

    # Update parties
    sheets_bossing.update_parties(new_sheets_parties)


def __update_existing_party(discord_party):
    # Update party status and member count
    new_sheets_parties = sheets_bossing.parties
    for sheets_party in new_sheets_parties:
        if sheets_party.role_id == str(discord_party.id):  # The relevant party data
            sheets_party.member_count = str(len(discord_party.members))
            if sheets_party.status == SheetsParty.PartyStatus.open.name and len(discord_party.members) == 6:
                # Update to full if it is open
                sheets_party.status = SheetsParty.PartyStatus.full.name
            elif sheets_party.status == SheetsParty.PartyStatus.full.name and len(discord_party.members) < 6:
                # Update to open if it is full
                sheets_party.status = SheetsParty.PartyStatus.open.name
            elif discord_party.name.find('Retired') != -1:
                # Update to retired
                sheets_party.status = SheetsParty.PartyStatus.retired.name
                sheets_party.boss_list_message_id = ''
                sheets_party.boss_list_decorator_id = ''
            break

    sheets_bossing.update_parties(new_sheets_parties)


async def __update_boss_party_list_message(message, sheets_party: SheetsParty,
                                           party_sheets_members: list[SheetsMember] = None):
    if party_sheets_members is None:
        party_sheets_members = []
        sheets_members = sheets_bossing.members

        for sheets_member in sheets_members:
            if sheets_member.party_role_id == sheets_party.role_id:
                party_sheets_members.append(sheets_member)

    message_content = f'<@&{sheets_party.role_id}>'
    if sheets_party.party_thread_id:
        message_content += f' <#{sheets_party.party_thread_id}>'
    message_content += '\n'
    timestamp = sheets_party.next_scheduled_time()
    if timestamp:
        message_content += f'**Next run:** <t:{timestamp}:F> <t:{timestamp}:R>\n'
    for sheets_member in party_sheets_members:
        message_content += f'<@{sheets_member.user_id}> {sheets_member.job}\n'
    if sheets_party.status == SheetsParty.PartyStatus.open.name or sheets_party.status == SheetsParty.PartyStatus.new.name:
        for n in range(0, 6 - int(sheets_party.member_count)):
            message_content += 'Open\n'

    await message.edit(content=message_content)
