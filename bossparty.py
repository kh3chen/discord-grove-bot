import asyncio
from functools import reduce

import discord

import config
from bosstimeupdater import BossTimeUpdater
from sheets_bossing import Member as SheetsMember
from sheets_bossing import Party as SheetsParty
from sheets_bossing import SheetsBossing


class BossParty:
    JOBS = ['Hero', 'Paladin', 'Dark Knight', 'Arch Mage (F/P)', 'Arch Mage (I/L)', 'Bishop', 'Bowmaster', 'Marksman',
            'Pathfinder', 'Night Lord', 'Shadower', 'Blade Master', 'Buccaneer', 'Corsair', 'Cannon Master',
            'Dawn Warrior', 'Blaze Wizard', 'Wind Archer', 'Night Walker', 'Thunder Breaker', 'Aran', 'Evan',
            'Mercedes', 'Phantom', 'Shade', 'Luminous', 'Demon Slayer', 'Demon Avenger', 'Battle Mage', 'Wild Hunter',
            'Mechanic', 'Xenon', 'Blaster', 'Hayato', 'Kanna', 'Mihile', 'Kaiser', 'Kain', 'Cadena', 'Angelic Buster',
            'Zero', 'Beast Tamer', 'Kinesis', 'Adele', 'Illium', 'Khali', 'Ark', 'Lara', 'Hoyoung']

    def __init__(self, bot):
        self.bot = bot
        self.lock = asyncio.Lock()
        self.sheets_bossing = SheetsBossing()

        async def on_reminder(sheets_party: SheetsParty):
            # Send reminder in party thread
            if sheets_party.party_thread_id:
                boss_forum = self.bot.get_channel(
                    int(self.sheets_bossing.bosses_dict[sheets_party.boss_name].forum_channel_id))
                party_thread = boss_forum.get_thread(int(sheets_party.party_thread_id))
                timestamp = sheets_party.next_scheduled_time()
                message = f'{sheets_party.get_mention()}\n**Next run:** <t:{timestamp}:F> <t:{timestamp}:R>\n\n'
                message += f'React to confirm your availability. If you are unable to make this run, please follow Grove\'s bossing etiquette found in <#{config.GROVE_CHANNEL_ID_BOSS_PARTY_LIST}>. Thank you!'
                await party_thread.send(message)

        async def on_update(sheets_party: SheetsParty):
            if sheets_party.boss_list_message_id:
                # Update boss list message
                boss_party_list_channel = self.bot.get_channel(config.GROVE_CHANNEL_ID_BOSS_PARTY_LIST)
                message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
                await self.__update_boss_party_list_message(None, message, sheets_party)

            if sheets_party.party_thread_id:
                # Update thread
                boss_forum = self.bot.get_channel(
                    int(self.sheets_bossing.bosses_dict[sheets_party.boss_name].forum_channel_id))
                party_thread = boss_forum.get_thread(int(sheets_party.party_thread_id))
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self.__update_thread(None, party_thread, party_message, sheets_party)

        self.boss_time_updater = BossTimeUpdater(on_reminder, on_update)
        self.restart_updater()

    def restart_updater(self):
        self.boss_time_updater.restart_updater(self.sheets_bossing.parties)

    async def scrape(self, ctx):
        """ Used in the initial set up for the Boss Parties spreadsheet data, this function should no longer have any use."""
        discord_parties = self.__get_boss_parties(ctx.guild.roles)

        # Update parties data
        async with self.lock:
            parties_pairs = self.__update_with_new_parties(discord_parties)

            # Update members data
            new_sheets_members = []
            for discord_party, sheets_party in parties_pairs:
                for member in discord_party.members:
                    member_user_id = str(member.id)
                    try:
                        next(
                            sheets_member for sheets_member in self.sheets_bossing.members_dict[sheets_party.role_id] if
                            sheets_member.user_id == member_user_id and sheets_member.party_role_id == sheets_party.role_id)
                    except StopIteration:
                        # Not found in member sheet data, add new member
                        new_sheets_members.append(
                            SheetsMember(boss_name=sheets_party.boss_name, party_number=sheets_party.party_number,
                                         party_role_id=sheets_party.role_id, user_id=member_user_id, job=''))
                        continue

            self.sheets_bossing.append_members(new_sheets_members)
        await self.__send(ctx, 'Scrape complete.', ephemeral=True)

    async def sync(self, ctx):
        async with self.lock:
            self.sheets_bossing.sync_data()
        self.restart_updater()

        await self.__send(ctx, 'Sync complete.', ephemeral=True)

    async def add(self, ctx, member, discord_party, job):
        # Validate job
        if job not in self.JOBS:
            await self.__send(ctx, f'Error - `{job}` is not a valid job. Valid jobs are as follows:\n'
                                   f'`{reduce(lambda acc, val: acc + (", " if acc else "") + val, BossParty.JOBS)}`',
                              ephemeral=True)
            return

        async with self.lock:
            # Validate the party
            try:
                sheets_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                    sheets_party.role_id == str(discord_party.id))
            except StopIteration:
                await self.__send(ctx,
                                  f'Error - Unable to find party {discord_party.mention} in the boss parties data.',
                                  ephemeral=True)
                return

            # Add member to the party
            try:
                await self._add(ctx, member, discord_party, job, sheets_party)
            except Exception as e:
                await self.__send(ctx, str(e), ephemeral=True)
                return

            # Add/remove from fill party based on joined party status
            fill_party_id = self.sheets_bossing.bosses_dict[sheets_party.boss_name].fill_role_id
            if fill_party_id:  # Fill party exists
                if (sheets_party.status == SheetsParty.PartyStatus.new.name or
                        sheets_party.status == SheetsParty.PartyStatus.lfg.name):
                    # Added party status is New or LFG. Add to fill
                    discord_fill_party = ctx.guild.get_role(int(fill_party_id))
                    try:
                        sheets_fill_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                                 sheets_party.role_id == fill_party_id)
                    except StopIteration:
                        await self.__send(ctx,
                                          f'Error - Unable to find party {discord_party.mention} in the boss parties data.',
                                          ephemeral=True)
                        return

                    try:
                        await self._add(ctx, member, discord_fill_party, job, sheets_fill_party, silent=True)
                    except UserWarning:
                        # Member already has the fill role
                        return
                elif (sheets_party.status == SheetsParty.PartyStatus.open.name or
                      sheets_party.status == SheetsParty.PartyStatus.exclusive.name):
                    # Added party status is not New. Remove from LFG
                    lfg_party_id = self.sheets_bossing.bosses_dict[sheets_party.boss_name].lfg_role_id
                    discord_lfg_party = ctx.guild.get_role(int(lfg_party_id))
                    try:
                        sheets_lfg_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                                sheets_party.role_id == lfg_party_id)
                    except StopIteration:
                        await self.__send(ctx,
                                          f'Error - Unable to find party {discord_party.mention} in the boss parties data.',
                                          ephemeral=True)
                        return
                    try:
                        await self._remove(ctx, member, discord_lfg_party, job, sheets_lfg_party, silent=True)
                    except UserWarning:
                        # Member did not have the LFG role
                        return

                    # Added party status is not New. Remove from fill
                    discord_fill_party = ctx.guild.get_role(int(fill_party_id))
                    try:
                        sheets_fill_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                                 sheets_party.role_id == fill_party_id)
                    except StopIteration:
                        await self.__send(ctx,
                                          f'Error - Unable to find party {discord_party.mention} in the boss parties data.',
                                          ephemeral=True)
                        return
                    try:
                        await self._remove(ctx, member, discord_fill_party, job, sheets_fill_party, silent=True)
                    except UserWarning:
                        # Member did not have the fill role
                        return

    async def _add(self, ctx, member, discord_party, job, sheets_party, silent=False):
        if sheets_party.status == SheetsParty.PartyStatus.retired.name:
            raise Exception(f'Error - {discord_party.mention} is retired.')

        # Check if the party is already full
        if sheets_party.status != SheetsParty.PartyStatus.fill.name and sheets_party.member_count == '6':
            raise Exception(f'Error - {discord_party.mention} is full.')

        # Check if the user is already in the party
        try:
            found_discord_member = next(
                discord_member for discord_member in discord_party.members if discord_member.id == member.id)
        except StopIteration:
            found_discord_member = None

        if found_discord_member:
            # Can have multiple characters in fill
            try:
                found_sheets_member = next(
                    sheets_member for sheets_member in self.sheets_bossing.members_dict[sheets_party.role_id] if
                    sheets_member.user_id == str(member.id) and sheets_member.job == job)
            except StopIteration:
                found_sheets_member = None

            if found_sheets_member:
                raise UserWarning(f'Error - {member.mention} *{job}* is already in {discord_party.mention}.')

        # Add role to user
        await member.add_roles(discord_party)

        # Add member to member sheet
        self.sheets_bossing.append_members([SheetsMember(boss_name=sheets_party.boss_name,
                                                         party_number=sheets_party.party_number,
                                                         party_role_id=sheets_party.role_id, user_id=str(member.id),
                                                         job=job)])

        # Update party data
        self.__update_existing_party(discord_party)

        # Success
        await self.__send(ctx, f'Successfully added {member.mention} *{job}* to {discord_party.mention}.',
                          ephemeral=True)

        if sheets_party.boss_list_message_id:
            # Update boss list message
            boss_party_list_channel = self.bot.get_channel(config.GROVE_CHANNEL_ID_BOSS_PARTY_LIST)
            message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
            await self.__update_boss_party_list_message(ctx, message, sheets_party)

        if not silent:
            if sheets_party.party_thread_id:
                # Update thread title, message, and send update in party thread
                boss_forum = self.bot.get_channel(
                    int(self.sheets_bossing.bosses_dict[sheets_party.boss_name].forum_channel_id))
                party_thread = boss_forum.get_thread(int(sheets_party.party_thread_id))
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self.__update_thread(ctx, party_thread, party_message, sheets_party)
                await party_thread.send(f'{member.mention} *{job}* has been added to {discord_party.mention}.')
            else:
                # Send LFG and Fill updates in Sign Up thread
                sign_up_thread = self.bot.get_channel(
                    int(self.sheets_bossing.bosses_dict[sheets_party.boss_name].sign_up_thread_id))
                if sheets_party.status == SheetsParty.PartyStatus.lfg.name:
                    # Mention role
                    await sign_up_thread.send(f'{member.mention} *{job}* has been added to {discord_party.mention}.')
                elif sheets_party.status == SheetsParty.PartyStatus.fill.name:
                    # Do not mention role
                    await sign_up_thread.send(
                        f'{member.mention} *{job}* has been added to {sheets_party.boss_name} Fill.')

    async def remove(self, ctx, member, discord_party, job=''):
        # Validate that this is a boss party role
        try:
            sheets_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                sheets_party.role_id == str(discord_party.id))
        except StopIteration:
            await self.__send(ctx, f'Error - Unable to find party {discord_party.id} in the boss parties data.',
                              ephemeral=True)
            return

        async with self.lock:
            # Remove member from party
            try:
                removed_sheets_member = await self._remove(ctx, member, discord_party, job, sheets_party)
            except Exception as e:
                await self.__send(ctx, str(e), ephemeral=True)
                return

            # Remove from fill if the party is new or LFG
            fill_party_id = self.sheets_bossing.bosses_dict[sheets_party.boss_name].fill_role_id
            if fill_party_id:  # Fill party exists
                if (sheets_party.status == SheetsParty.PartyStatus.new.name or
                        sheets_party.status == SheetsParty.PartyStatus.lfg.name):
                    # Removed party status is New or LFG. Remove from fill
                    discord_fill_party = ctx.guild.get_role(int(fill_party_id))
                    try:
                        sheets_fill_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                                 sheets_party.role_id == fill_party_id)
                    except StopIteration:
                        await self.__send(ctx,
                                          f'Error - Unable to find party {discord_party.mention} in the boss parties data.',
                                          ephemeral=True)
                        return

                    try:
                        await self._remove(ctx, member, discord_fill_party, removed_sheets_member.job,
                                           sheets_fill_party, silent=True)
                    except UserWarning:
                        # Member did not have the fill role
                        return

    async def _remove(self, ctx, member, discord_party, job, sheets_party, silent=False, left_server=False):
        if not left_server:
            # Check if user has the role
            try:
                next(discord_member for discord_member in discord_party.members if discord_member.id == member.id)
            except StopIteration:
                raise UserWarning(f'Error - {member.mention} is not in {discord_party.mention}.')

        if (sheets_party.status != SheetsParty.PartyStatus.lfg.name and
                sheets_party.status != SheetsParty.PartyStatus.fill.name and
                job == ''):
            # Party cannot have multiple characters. Since job is unspecified, assume the single member is correct
            has_role_count = 1
            found_character = True
        else:
            # Either party status is lfg or fill, or job has been specified.
            has_role_count = 0
            found_character = False
            for sheets_member in self.sheets_bossing.members_dict[sheets_party.role_id]:
                if sheets_member.user_id == str(member.id):
                    has_role_count += 1
                    if sheets_member.job == job:
                        found_character = True
            if job == '':
                found_character = True

        # Remove role from user if only one character with role
        if has_role_count == 1 and found_character:
            if not left_server:
                # Can only remove role from an existing member
                await member.remove_roles(discord_party)
        elif has_role_count > 1 and found_character:
            # Keep fill role since they will still have another character
            pass
        elif has_role_count > 1 and not found_character and job == '':
            # More than one character with fill role, job must be specified
            raise Exception(f'Error - {member.mention} has more than one character with this role, please specify job.')
        else:
            raise Exception(f'Error - {member.mention} *{job}* is not in {discord_party.mention}.')

        # Remove member from member sheet
        removed_sheets_member = self.sheets_bossing.delete_member(
            SheetsMember(boss_name=sheets_party.boss_name, party_number=sheets_party.party_number,
                         party_role_id=sheets_party.role_id, user_id=str(member.id), job=job))

        # Update party data
        self.__update_existing_party(discord_party)

        # Success
        await self.__send(ctx,
                          f'Successfully removed {member.mention} *{removed_sheets_member.job}* from {discord_party.mention}.',
                          ephemeral=True)

        if sheets_party.boss_list_message_id:
            # Update boss list message
            boss_party_list_channel = self.bot.get_channel(config.GROVE_CHANNEL_ID_BOSS_PARTY_LIST)
            message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
            await self.__update_boss_party_list_message(ctx, message, sheets_party)

        if not silent:
            if sheets_party.party_thread_id:
                # Update thread title, message, and send update in party thread
                boss_forum = self.bot.get_channel(
                    int(self.sheets_bossing.bosses_dict[sheets_party.boss_name].forum_channel_id))
                party_thread = boss_forum.get_thread(int(sheets_party.party_thread_id))
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self.__update_thread(ctx, party_thread, party_message, sheets_party)
                await party_thread.send(
                    f'{member.mention} *{removed_sheets_member.job}* has been removed from {discord_party.mention}.')
            else:
                # Send LFG and Fill updates in Sign Up thread
                sign_up_thread = self.bot.get_channel(
                    int(self.sheets_bossing.bosses_dict[sheets_party.boss_name].sign_up_thread_id))
                if sheets_party.status == SheetsParty.PartyStatus.lfg.name:
                    # Do not mention role
                    await sign_up_thread.send(
                        f'{member.mention} *{removed_sheets_member.job}* has been removed from {sheets_party.boss_name} LFG.')
                elif sheets_party.status == SheetsParty.PartyStatus.fill.name:
                    # Do not mention role
                    await sign_up_thread.send(
                        f'{member.mention} *{removed_sheets_member.job}* has been removed from {sheets_party.boss_name} Fill.')

        return removed_sheets_member

    async def create(self, ctx, boss_name):
        if boss_name not in self.sheets_bossing.get_boss_names():
            await self.__send(ctx, f'Error - `{boss_name}` is not a valid boss name. Valid boss names are as follows:\n'
                                   f'`{reduce(lambda acc, val: acc + (", " if acc else "") + val, self.sheets_bossing.get_boss_names())}`',
                              ephemeral=True)
            return

        async with self.lock:
            discord_parties = self.__get_boss_parties(ctx.guild.roles)
            new_party_boss_index = self.sheets_bossing.get_boss_names().index(boss_name)
            party_number = 1
            new_boss_party = None

            # Find the correct position for the new role
            for discord_party in discord_parties:
                party_boss_index = self.sheets_bossing.get_boss_names().index(
                    discord_party.name[0:discord_party.name.find(' ')])
                if boss_name in discord_party.name:
                    if 'LFG' in discord_party.name:
                        # Found LFG party for the corresponding boss, insert new party above it
                        new_boss_party = await ctx.guild.create_role(name=f'{boss_name} Party {party_number}',
                                                                     colour=self.sheets_bossing.bosses_dict[
                                                                         boss_name].get_role_colour(), mentionable=True)
                        await new_boss_party.edit(position=discord_party.position)
                        discord_parties.insert(discord_parties.index(discord_party), new_boss_party)
                        break
                    else:
                        party_number += 1

                elif party_boss_index > new_party_boss_index:
                    # Found a party boss that comes after, insert new party above it
                    new_boss_party = await ctx.guild.create_role(name=f'{boss_name} Party {party_number}',
                                                                 colour=self.sheets_bossing.bosses_dict[
                                                                     boss_name].get_role_colour(), mentionable=True)
                    await new_boss_party.edit(position=discord_party.position)
                    discord_parties.insert(discord_parties.index(discord_party), new_boss_party)
                    break

            if new_boss_party is None:
                # Couldn't find any of the above, new party must come last
                new_boss_party = await ctx.guild.create_role(name=f'{boss_name} Party {party_number}',
                                                             colour=self.sheets_bossing.bosses_dict[
                                                                 boss_name].get_role_colour(), mentionable=True)
                await new_boss_party.edit(position=discord_parties[-1].position)
                discord_parties.append(new_boss_party)

            # Update spreadsheet
            self.__update_with_new_parties(discord_parties)

            # Create thread
            boss_forum = self.bot.get_channel(int(self.sheets_bossing.bosses_dict[boss_name].forum_channel_id))
            party_thread_with_message = await boss_forum.create_thread(name=f'{new_boss_party.name} - New',
                                                                       content=f'{new_boss_party.mention}')
            await self.__send(ctx,
                              f'Created thread {party_thread_with_message.thread.mention} for {new_boss_party.mention}.',
                              ephemeral=True)
            sheets_parties = self.sheets_bossing.parties
            for sheets_party in sheets_parties:
                if sheets_party.role_id == str(new_boss_party.id):
                    sheets_party.party_thread_id = party_thread_with_message.thread.id
                    sheets_party.party_message_id = party_thread_with_message.message.id
                    break
            self.sheets_bossing.update_parties(sheets_parties)

            await self.__send(ctx, f'Successfully created {new_boss_party.name}.', ephemeral=True)

            # Remake boss party list
            await self.__remake_boss_party_list(ctx)

    async def settime(self, ctx, discord_party, weekday_str, hour, minute):
        weekday = SheetsParty.Weekday[weekday_str]
        if not weekday:
            await self.__send(ctx,
                              'Error - Invalid weekday. Valid input values: [ mon | tue | wed | thu | fri | sat | sun ]',
                              ephemeral=True)
            return

        if hour < 0 or hour > 23:
            await self.__send(ctx, 'Error - Invalid hour. Hour must be from 0-23.', ephemeral=True)
            return

        if minute < 0 or minute > 59:
            await self.__send(ctx, 'Error - Invalid minute. Minute must be from 0-59.', ephemeral=True)
            return

        async with self.lock:
            sheets_parties = self.sheets_bossing.parties
            try:
                sheets_party = next(
                    sheets_party for sheets_party in sheets_parties if sheets_party.role_id == str(discord_party.id))
            except StopIteration:
                await self.__send(ctx,
                                  f'Error - Unable to find party {discord_party.mention} in the boss parties data.',
                                  ephemeral=True)
                return

            if sheets_party.status == SheetsParty.PartyStatus.retired.name:
                await ctx.send(f'Error - {discord_party.mention} is retired.')
                return

            if sheets_party.status == SheetsParty.PartyStatus.lfg.name or sheets_party.status == SheetsParty.PartyStatus.fill.name:
                await ctx.send(f'Error - {discord_party.mention} is not a party.')
                return

            sheets_party.weekday = weekday.name
            sheets_party.hour = str(hour)
            sheets_party.minute = str(minute)
            self.sheets_bossing.update_parties(sheets_parties)
            self.restart_updater()
            timestamp = sheets_party.next_scheduled_time()

            message_content = f'Set {discord_party.mention} time to {weekday.name} at +{hour}:{minute:02d}.\n'
            message_content += f'Next run: <t:{timestamp}:F>'
            await self.__send(ctx, message_content, ephemeral=True)

            if sheets_party.boss_list_message_id:
                # Update boss list message
                boss_party_list_channel = self.bot.get_channel(config.GROVE_CHANNEL_ID_BOSS_PARTY_LIST)
                message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
                await self.__update_boss_party_list_message(ctx, message, sheets_party)

            if sheets_party.party_thread_id:
                # Update thread title, message, and send update in party thread
                boss_forum = self.bot.get_channel(
                    int(self.sheets_bossing.bosses_dict[sheets_party.boss_name].forum_channel_id))
                party_thread = boss_forum.get_thread(int(sheets_party.party_thread_id))
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self.__update_thread(ctx, party_thread, party_message, sheets_party)
                await party_thread.send(
                    f'{discord_party.mention} time has been updated.\n**Next run:** <t:{timestamp}:F> <t:{timestamp}:R>')

    async def cleartime(self, ctx, discord_party):
        async with self.lock:
            sheets_parties = self.sheets_bossing.parties
            try:
                sheets_party = next(
                    sheets_party for sheets_party in sheets_parties if sheets_party.role_id == str(discord_party.id))
            except StopIteration:
                await self.__send(ctx,
                                  f'Error - Unable to find party {discord_party.mention} in the boss parties data.',
                                  ephemeral=True)
                return

            if sheets_party.status == SheetsParty.PartyStatus.retired.name:
                await ctx.send(f'Error - {discord_party.mention} is retired.')
                return

            if sheets_party.status == SheetsParty.PartyStatus.lfg.name or sheets_party.status == SheetsParty.PartyStatus.fill.name:
                await ctx.send(f'Error - {discord_party.mention} is not a party.')
                return

            sheets_party.weekday = ''
            sheets_party.hour = ''
            sheets_party.minute = ''
            self.sheets_bossing.update_parties(sheets_parties)
            self.restart_updater()

            await self.__send(ctx, f'Cleared {discord_party.mention} time.', ephemeral=True)

            if sheets_party.boss_list_message_id:
                # Update boss list message
                boss_party_list_channel = self.bot.get_channel(config.GROVE_CHANNEL_ID_BOSS_PARTY_LIST)
                message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
                await self.__update_boss_party_list_message(ctx, message, sheets_party)

            if sheets_party.party_thread_id:
                # Update thread title, message, and send update in party thread
                boss_forum = self.bot.get_channel(
                    int(self.sheets_bossing.bosses_dict[sheets_party.boss_name].forum_channel_id))
                party_thread = boss_forum.get_thread(int(sheets_party.party_thread_id))
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self.__update_thread(ctx, party_thread, party_message, sheets_party)
                await party_thread.send(f'{discord_party.mention} time has been cleared.')

    async def retire(self, ctx, discord_party):
        # Validate that this is a boss party role
        try:
            sheets_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                sheets_party.role_id == str(discord_party.id))
        except StopIteration:
            await self.__send(ctx, f'Error - {discord_party.mention} is not a boss party.', ephemeral=True)
            return

        if sheets_party.status == SheetsParty.PartyStatus.retired.name:
            await self.__send(ctx, f'Error - {discord_party.mention} is already retired.', ephemeral=True)
            return

        if sheets_party.status == SheetsParty.PartyStatus.new.name:
            await self.__send(ctx, f'Error - {discord_party.mention} is new, you cannot retire a new party.',
                              ephemeral=True)
            return

        # Confirmation
        confirmation_message_body = f'Are you sure you want to retire {discord_party.mention}? The following {len(discord_party.members)} member(s) will be removed from the party:\n'
        for member in discord_party.members:
            confirmation_message_body += f'{member.mention}\n'
        confirmation_message_body += f'\nReact with 👍 to proceed.'

        confirmation_message = await self.__send(ctx, confirmation_message_body)
        await confirmation_message.add_reaction('👍')

        def check(reaction, user):
            print(reaction)
            return user == ctx.author and str(reaction.emoji) == '👍'

        try:
            await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await self.__send(ctx, 'Error - confirmation expired. Party retire has been cancelled.', ephemeral=True)
            return

        # Remove members from party
        for member in discord_party.members:
            await self.remove(ctx, member, discord_party)

        async with self.lock:
            # Update party status to retired
            discord_party = await discord_party.edit(name=f'{discord_party.name} (Retired)', mentionable=False)

            # Delete boss party list messages
            boss_party_list_channel = self.bot.get_channel(config.GROVE_CHANNEL_ID_BOSS_PARTY_LIST)
            if sheets_party.boss_list_message_id:
                message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
                await message.delete()
            if sheets_party.boss_list_decorator_id:
                message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_decorator_id)
                await message.delete()

            self.__update_existing_party(discord_party)
            self.restart_updater()

            if sheets_party.party_thread_id:
                # Update thread title, message, and send update in party thread
                boss_forum = self.bot.get_channel(
                    int(self.sheets_bossing.bosses_dict[sheets_party.boss_name].forum_channel_id))
                party_thread = boss_forum.get_thread(int(sheets_party.party_thread_id))
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self.__update_thread(ctx, party_thread, party_message, sheets_party)

        await self.__send(ctx, f'{discord_party.mention} has been retired.', ephemeral=True)

    async def exclusive(self, ctx, discord_party):
        await self.__update_status(ctx, discord_party, SheetsParty.PartyStatus.exclusive)

    async def open(self, ctx, discord_party):
        await self.__update_status(ctx, discord_party, SheetsParty.PartyStatus.open)

    async def __update_status(self, ctx, discord_party, status):
        async with self.lock:
            sheets_parties = self.sheets_bossing.parties
            try:
                sheets_party = next(
                    sheets_party for sheets_party in sheets_parties if sheets_party.role_id == str(discord_party.id))
            except StopIteration:
                await self.__send(ctx, f'Error - {discord_party.mention} is not a boss party.', ephemeral=True)
                return

            if sheets_party.status == SheetsParty.PartyStatus.retired.name:
                await self.__send(ctx, f'Error - {discord_party.mention} is retired and cannot be reopened.',
                                  ephemeral=True)
                return

            if sheets_party.status == status.name:
                await self.__send(ctx, f'Error - {discord_party.mention} is already {status.name}.', ephemeral=True)
                return

            if status != SheetsParty.PartyStatus.exclusive and status != SheetsParty.PartyStatus.open:
                await self.__send(ctx, f'Error - {discord_party.mention} cannot be {status.name}.', ephemeral=True)

            if sheets_party.status == SheetsParty.PartyStatus.new.name:
                # Remove fill roles of members if changing status from new
                fill_party_id = self.sheets_bossing.bosses_dict[sheets_party.boss_name].fill_role_id
                if fill_party_id:  # Fill party exists
                    discord_fill_party = ctx.guild.get_role(int(fill_party_id))
                    try:
                        sheets_fill_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                                 sheets_party.role_id == fill_party_id)

                        for discord_member in discord_party.members:
                            try:
                                sheets_member = next(
                                    sheets_member for sheets_member in self.sheets_bossing.members_dict[fill_party_id]
                                    if sheets_member.user_id == str(discord_member.id))
                                try:
                                    await self._remove(ctx, discord_member, discord_fill_party, sheets_member.job,
                                                       sheets_fill_party, silent=True)
                                except Exception as e:
                                    await self.__send(ctx, str(e), ephemeral=True)
                            except StopIteration:
                                await self.__send(ctx,
                                                  f'Error - Unable to find {discord_member.mention} in {discord_party.mention}.',
                                                  ephemeral=True)
                    except StopIteration:
                        await self.__send(ctx,
                                          f'Error - Unable to find party {discord_party.mention} in the boss parties data.',
                                          ephemeral=True)

            sheets_party.status = status.name
            self.sheets_bossing.update_parties(sheets_parties)
            await self.__send(ctx, f'{discord_party.name} is now {sheets_party.status}.', ephemeral=True)

            if sheets_party.boss_list_message_id:
                # Update boss list message
                boss_party_list_channel = self.bot.get_channel(config.GROVE_CHANNEL_ID_BOSS_PARTY_LIST)
                message = await boss_party_list_channel.fetch_message(sheets_party.boss_list_message_id)
                await self.__update_boss_party_list_message(ctx, message, sheets_party)

            if sheets_party.party_thread_id:
                # Update thread title, message, and send update in party thread
                boss_forum = self.bot.get_channel(
                    int(self.sheets_bossing.bosses_dict[sheets_party.boss_name].forum_channel_id))
                party_thread = boss_forum.get_thread(int(sheets_party.party_thread_id))
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self.__update_thread(ctx, party_thread, party_message, sheets_party)

    async def listremake(self, ctx):
        # Confirmation
        confirmation_message_body = f'Are you sure you want to remake the boss party list in <#{config.GROVE_CHANNEL_ID_BOSS_PARTY_LIST}>?\n'
        confirmation_message_body += f'\nReact with 👍 to proceed.'

        confirmation_message = await self.__send(ctx, confirmation_message_body)
        await confirmation_message.add_reaction('👍')

        def check(reaction, user):
            print(reaction)
            return user == ctx.author and str(reaction.emoji) == '👍'

        try:
            await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await self.__send(ctx, 'Error - confirmation expired. Party retire has been cancelled.', ephemeral=True)
            return

        async with self.lock:
            await self.__remake_boss_party_list(ctx)

    async def on_member_remove(self, member: discord.Member):
        async with self.lock:
            discord_parties = self.__get_boss_parties(member.roles)
            for discord_party in discord_parties:
                try:
                    sheets_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                        sheets_party.role_id == str(discord_party.id))
                except StopIteration:
                    # Couldn't find the party
                    continue

                try:
                    sheets_member = next(sheets_member for sheets_member in self.sheets_bossing.members if
                                         sheets_member.user_id == str(member.id) and sheets_member.party_role_id == str(
                                             discord_party.id))
                except StopIteration:
                    # Couldn't find the member
                    continue

                try:
                    await self._remove(None, member, discord_party, sheets_member.job, sheets_party,
                                       silent=sheets_party.status == SheetsParty.PartyStatus.fill.name,
                                       left_server=True)
                except Exception as e:
                    await self.__send(None, str(e))

    async def __remake_boss_party_list(self, ctx):
        # Delete existing messages
        boss_party_list_channel = self.bot.get_channel(config.GROVE_CHANNEL_ID_BOSS_PARTY_LIST)

        new_sheets_parties = self.sheets_bossing.parties

        await self.__send(ctx, 'Deleting the existing boss party list...', ephemeral=True)
        await boss_party_list_channel.purge(limit=len(new_sheets_parties) * 2)

        try:
            for sheets_party in new_sheets_parties:
                sheets_party.boss_list_message_id = ''
                sheets_party.boss_list_decorator_id = ''
        except IndexError:
            return

        self.sheets_bossing.update_parties(new_sheets_parties)

        await self.__send(ctx, 'Existing boss party list deleted.', ephemeral=True)

        # Send the boss party messages
        await self.__send(ctx, 'Creating the new boss party list...', ephemeral=True)

        current_sheets_boss = None
        for sheets_party in new_sheets_parties:
            if sheets_party.status == SheetsParty.PartyStatus.retired.name:
                continue

            # Send section title
            if not current_sheets_boss or current_sheets_boss.boss_name != sheets_party.boss_name:
                current_sheets_boss = self.sheets_bossing.bosses_dict[sheets_party.boss_name]
                section_title_content = f'# {current_sheets_boss.human_readable_name}'
                message = await boss_party_list_channel.send(section_title_content)
                sheets_party.boss_list_decorator_id = str(message.id)
            else:
                message = await boss_party_list_channel.send('_ _')
                sheets_party.boss_list_decorator_id = str(message.id)

            # Placeholder first to avoid mention
            message = await boss_party_list_channel.send(f'{sheets_party.boss_name} Party {sheets_party.party_number}')
            sheets_party.boss_list_message_id = str(message.id)

            await self.__update_boss_party_list_message(ctx, message, sheets_party,
                                                        self.sheets_bossing.members_dict[sheets_party.role_id])

        etiquette_message = ('# Bossing etiquette'
                             '\n\nWith organized bossing, it is important that all party members are in attendance to ensure a smooth clear. Out of respect for your fellow guildmates, please follow Grove\'s bossing etiquette:'
                             '\n1. Be on time.'
                             '\n2. If you are unable to make boss run time for the week, let your party know as soon as possible, and organize another time for your party that week.'
                             '\n3. If you are unable to make the boss run at all for a week, let your party know as soon as possible, and find a fill for your spot.')
        await boss_party_list_channel.send(etiquette_message)

        self.sheets_bossing.update_parties(new_sheets_parties)

        await self.__send(ctx, 'New boss party list complete.', ephemeral=True)

    def __get_boss_parties(self, discord_roles):
        """Returns the subset of Grove boss party roles from a list of Discord roles."""
        # get all boss party roles by matching their names to the bosses
        parties = []
        for role in discord_roles:
            if role.name.find(' ') == -1 or role.name.find('Practice') != -1:
                continue

            if role.name[0:role.name.find(' ')] in self.sheets_bossing.get_boss_names():
                parties.append(role)

        parties.reverse()  # Roles are ordered bottom up
        return parties

    def __update_with_new_parties(self, discord_parties):
        parties_pairs = []
        # get list of parties from sheet
        sheets_parties = self.sheets_bossing.parties
        added_sheets_parties = []
        parties_values_index = 0

        for discord_party in discord_parties:
            if parties_values_index == len(sheets_parties):
                # More party roles than in data, new party at the end
                new_sheets_party = SheetsParty.from_discord_party(discord_party)
                sheets_parties.append(new_sheets_party)
                added_sheets_parties.append(new_sheets_party)
                parties_pairs.append((discord_party, new_sheets_party))
            elif sheets_parties[parties_values_index].role_id != str(discord_party.id):
                # Party role doesn't match data, there must be a new record
                new_sheets_party = SheetsParty.from_discord_party(discord_party)
                sheets_parties.insert(parties_values_index, new_sheets_party)
                added_sheets_parties.append(new_sheets_party)
                parties_pairs.append((discord_party, new_sheets_party))
            else:  # Data exists
                parties_pairs.append((discord_party, sheets_parties[parties_values_index]))

            parties_values_index += 1

        # Update parties
        self.sheets_bossing.update_parties(sheets_parties, added_sheets_parties)

        return parties_pairs

    def __update_existing_party(self, discord_party):
        # Update party status and member count
        new_sheets_parties = self.sheets_bossing.parties
        for sheets_party in new_sheets_parties:
            if sheets_party.role_id == str(discord_party.id):  # Found the existing party we want to update
                sheets_party.member_count = str(len(self.sheets_bossing.members_dict[sheets_party.role_id]))
                if discord_party.name.find('Retired') != -1:
                    # Update to retired
                    sheets_party.status = SheetsParty.PartyStatus.retired.name
                    sheets_party.weekday = ''
                    sheets_party.hour = ''
                    sheets_party.minute = ''
                    sheets_party.boss_list_message_id = ''
                    sheets_party.boss_list_decorator_id = ''
                break

        self.sheets_bossing.update_parties(new_sheets_parties)

    async def __update_boss_party_list_message(self, ctx, message: discord.Message, sheets_party: SheetsParty,
                                               party_sheets_members: list[SheetsMember] = None):
        if party_sheets_members is None:
            party_sheets_members = self.sheets_bossing.members_dict[sheets_party.role_id]

        message_content = f'<@&{sheets_party.role_id}>'
        if sheets_party.party_thread_id:
            message_content += f' <#{sheets_party.party_thread_id}>'
        message_content += '\n'
        timestamp = sheets_party.next_scheduled_time()
        if timestamp:
            message_content += f'**Next run:** <t:{timestamp}:F> <t:{timestamp}:R>\n'
        for sheets_member in party_sheets_members:
            message_content += f'<@{sheets_member.user_id}> *{sheets_member.job}*\n'
        if sheets_party.status == SheetsParty.PartyStatus.open.name or sheets_party.status == SheetsParty.PartyStatus.new.name:
            for n in range(0, 6 - int(sheets_party.member_count)):
                message_content += 'Open\n'
        elif sheets_party.status == SheetsParty.PartyStatus.lfg.name and len(party_sheets_members) == 0:
            message_content += '*No members looking for group at this time*'
        elif sheets_party.status == SheetsParty.PartyStatus.fill.name and len(party_sheets_members) == 0:
            message_content += '*No members available to fill at this time*'

        await message.edit(content=message_content)

        await self.__send(ctx,
                          content=f'Boss party list message updated for <@&{sheets_party.role_id}>:\n{message.jump_url}',
                          ephemeral=True, suppress_embeds=True)

    async def __update_thread(self, ctx, party_thread: discord.Thread, party_message: discord.Message,
                              sheets_party: SheetsParty):
        # Update thread title
        title = f'{sheets_party.boss_name} Party {sheets_party.party_number} - '
        if sheets_party.status == SheetsParty.PartyStatus.retired.name:
            if party_message:
                message = f'<@&{sheets_party.role_id}>'
                await party_message.edit(content=message)
            title += 'Retired'

            await party_thread.edit(name=title, archived=True, locked=True)
        else:
            if sheets_party.status == SheetsParty.PartyStatus.new.name:
                title += 'New'
            elif sheets_party.status == SheetsParty.PartyStatus.exclusive.name or sheets_party.status == SheetsParty.PartyStatus.open.name and sheets_party.member_count == '6':
                title += 'Full'
            else:
                title += 'Open'

            if party_message:
                message = f'<@&{sheets_party.role_id}>'
                timestamp = sheets_party.next_scheduled_time()
                if timestamp:
                    message += f'\n**Next run:** <t:{timestamp}:F> <t:{timestamp}:R>'
                await party_message.edit(content=message)

            await party_thread.edit(name=title)

        await self.__send(ctx,
                          content=f'Boss party thread updated for <@&{sheets_party.role_id}>:\n{party_thread.mention}',
                          ephemeral=True, suppress_embeds=True)

    async def __send(self, ctx, content, ephemeral=False, suppress_embeds=False):
        if ctx:
            return await ctx.send(content=content, ephemeral=ephemeral, suppress_embeds=suppress_embeds)
        else:
            modlog_channel = self.bot.get_channel(config.GROVE_CHANNEL_ID_MODLOG)
            return await modlog_channel.send(content)
