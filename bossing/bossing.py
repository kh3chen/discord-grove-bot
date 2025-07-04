import asyncio
from datetime import datetime
from functools import reduce

import discord

import config
from bossing.service import BossTimeService
from bossing.sheets import BossingSheets
from bossing.sheets import Member as SheetsMember
from bossing.sheets import NoShow as SheetsNoShow
from bossing.sheets import Party as SheetsParty


class Bossing:
    JOBS = ['Hero', 'Paladin', 'Dark Knight', 'Arch Mage (F/P)', 'Arch Mage (I/L)', 'Bishop', 'Bowmaster', 'Marksman',
            'Pathfinder', 'Night Lord', 'Shadower', 'Blade Master', 'Buccaneer', 'Corsair', 'Cannon Master',
            'Dawn Warrior', 'Blaze Wizard', 'Wind Archer', 'Night Walker', 'Thunder Breaker', 'Aran', 'Evan',
            'Mercedes', 'Phantom', 'Shade', 'Luminous', 'Demon Slayer', 'Demon Avenger', 'Battle Mage', 'Wild Hunter',
            'Mechanic', 'Xenon', 'Blaster', 'Hayato', 'Kanna', 'Mihile', 'Kaiser', 'Kain', 'Cadena', 'Angelic Buster',
            'Zero', 'Lynn', 'Kinesis', 'Adele', 'Illium', 'Khali', 'Ark', 'Lara', 'Hoyoung']

    def __init__(self, client):
        self.client = client
        self.lock = asyncio.Lock()
        self.sheets_bossing = BossingSheets()

        async def is_run_cancelled(sheets_party: SheetsParty, reactions: list[discord.Reaction]) -> bool:
            reacted_cancel = set()
            for reaction in reactions:
                if str(reaction.emoji) == '🕒' or str(reaction.emoji) == '❌':
                    reacted_cancel.update(
                        set(map(lambda user: str(user.id), [user async for user in reaction.users()])))

            reacted_cancel_party_members = set(filter(lambda member: member.user_id in reacted_cancel,
                                                      self.sheets_bossing.members_dict[sheets_party.role_id]))
            return len(reacted_cancel_party_members) >= (
                    len(self.sheets_bossing.members_dict[sheets_party.role_id]) + 1) / 2

        async def on_check_in(sheets_party: SheetsParty):
            # Send check-in message in party thread
            if sheets_party.party_thread_id:
                party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                message_content = self.__get_boss_party_list_message(sheets_party,
                                                                     self.sheets_bossing.members_dict[
                                                                         sheets_party.role_id])
                message_content += (f'\n**Check in for your upcoming boss run:**'
                                    f'\n✅ Accept'
                                    f'\n❌ Decline'
                                    f'\n🕒 Reschedule'
                                    f'\n\nReact with 🔔 to receive a reminder 15 minutes before the the scheduled boss run.'
                                    f'\n\nRepeated lack of communication with your party may result in removal from Grove bossing parties. Read the bossing etiquette here: <#{config.GROVE_CHANNEL_ID_BOSSING_PARTIES}>')
                message = await party_thread.send(message_content)
                await message.add_reaction('✅')
                await message.add_reaction('❌')
                await message.add_reaction('🕒')
                await message.add_reaction('🔔')
                sheets_party.check_in_message_id = message.id
                self.sheets_bossing.update_parties(self.sheets_bossing.parties)

        async def on_check_in_reminder(sheets_party: SheetsParty):
            # Send reminder in party thread to people who didn't react
            if sheets_party.party_thread_id and sheets_party.check_in_message_id:
                party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                check_in_message = await party_thread.fetch_message(sheets_party.check_in_message_id)
                if await is_run_cancelled(sheets_party, check_in_message.reactions):
                    return

                reacted = set()
                for reaction in check_in_message.reactions:
                    reacted.update(set(map(lambda user: str(user.id), [user async for user in reaction.users()])))

                away = set(map(lambda member: str(member.id), self.client.get_guild(config.GROVE_GUILD_ID).get_role(
                    config.GROVE_ROLE_ID_AWAY).members))
                party_members_not_reacted = list(filter(
                    lambda member: member.user_id not in reacted and member.user_id not in away,
                    self.sheets_bossing.members_dict[sheets_party.role_id]))
                if len(party_members_not_reacted) > 0:
                    reminder_message_content = f'**Reminder to check in for your upcoming boss run:** {check_in_message.jump_url}\n'
                    timestamp = sheets_party.next_scheduled_time()
                    if timestamp:
                        reminder_message_content += f'**Next run:** <t:{timestamp}:F> <t:{timestamp}:R>\n\n'
                    for sheets_member in party_members_not_reacted:
                        reminder_message_content += f'<@{sheets_member.user_id}> *{sheets_member.job}*\n'
                    reminder_message_content += f'\nRepeated lack of communication with your party may result in removal from Grove bossing parties. Read the bossing etiquette here: <#{config.GROVE_CHANNEL_ID_BOSSING_PARTIES}>'
                    await party_thread.send(reminder_message_content)

        async def on_requested_reminder(sheets_party: SheetsParty):
            # Send reminder in party thread to people who requested it
            if sheets_party.party_thread_id and sheets_party.check_in_message_id:
                party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                check_in_message = await party_thread.fetch_message(sheets_party.check_in_message_id)
                if await is_run_cancelled(sheets_party, check_in_message.reactions):
                    return

                for reaction in check_in_message.reactions:
                    if str(reaction.emoji) == '🔔':
                        reacted_reminder_users = list(filter(lambda user: user.id != config.GROVE_BOT_USER_ID,
                                                             map(lambda user: user,
                                                                 [user async for user in reaction.users()])))
                        timestamp = sheets_party.next_scheduled_time()
                        if len(reacted_reminder_users) > 0 and timestamp:
                            reminder_message_content = f'🔔 You have an upcoming **{sheets_party.name()}** boss run <t:{timestamp}:R>.\n'
                            for user in reacted_reminder_users:
                                reminder_message_content += f'\n{user.mention}'
                            await party_thread.send(reminder_message_content)

        async def on_run_start(sheets_party: SheetsParty):
            if sheets_party.party_thread_id:
                party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                if sheets_party.check_in_message_id:
                    # Check if run has been cancelled
                    check_in_message = await party_thread.fetch_message(sheets_party.check_in_message_id)
                    if await is_run_cancelled(sheets_party, check_in_message.reactions):
                        return
            if sheets_party.party_thread_id:
                # Send run start message in party thread
                party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                await party_thread.send(f'{sheets_party.mention()} run has begun!')

        async def on_update(sheets_party: SheetsParty):
            if sheets_party.boss_list_message_id:
                # Update bossing list message
                bossing_parties_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_BOSSING_PARTIES)
                message = await bossing_parties_channel.fetch_message(sheets_party.boss_list_message_id)
                await self.update_boss_party_list_message(message, sheets_party)

            if sheets_party.party_thread_id:
                # Update thread
                party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self._update_thread(party_thread, party_message, sheets_party)

                if sheets_party.check_in_message_id:
                    # Track non-responders to the check-in that don't have the Away role
                    check_in_message = await party_thread.fetch_message(sheets_party.check_in_message_id)
                    reacted = set()
                    for reaction in check_in_message.reactions:
                        reacted.update(set(map(lambda user: str(user.id), [user async for user in reaction.users()])))
                    away = set(map(lambda member: str(member.id), self.client.get_guild(config.GROVE_GUILD_ID).get_role(
                        config.GROVE_ROLE_ID_AWAY).members))
                    party_members_not_reacted = filter(
                        lambda member: member.user_id not in reacted and member.user_id not in away,
                        self.sheets_bossing.members_dict[sheets_party.role_id])
                    no_shows = list(map(lambda member: SheetsNoShow(sheets_party.next_scheduled_time() - 604800,
                                                                    member.user_id,
                                                                    sheets_party.role_id,
                                                                    sheets_party.boss_name,
                                                                    sheets_party.party_number),
                                        party_members_not_reacted))
                    print(no_shows)
                    self.sheets_bossing.append_no_shows(no_shows)

        self.boss_time_service = BossTimeService(on_check_in,
                                                 on_check_in_reminder,
                                                 on_requested_reminder,
                                                 on_run_start,
                                                 on_update)

    def _restart_service(self):
        self.boss_time_service.restart_service(self.sheets_bossing.parties)

    def on_ready(self):
        self._restart_service()

    async def sync(self, interaction):
        async with self.lock:
            self.sheets_bossing.sync_data()
        self._restart_service()

        await self._send(interaction, 'Sync complete.', ephemeral=True)

    async def add(self, interaction, member, discord_party, job):
        # Validate job
        if job not in self.JOBS:
            await self._send(interaction, f'Error - `{job}` is not a valid job. Valid jobs are as follows:\n'
                                          f'`{reduce(lambda acc, val: acc + (", " if acc else "") + val, Bossing.JOBS)}`',
                             ephemeral=True)
            return

        async with self.lock:
            # Validate the party
            try:
                sheets_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                    sheets_party.role_id == str(discord_party.id))
            except StopIteration:
                await self._send(interaction,
                                 f'Error - Unable to find party {discord_party.mention} in the bossing parties data.',
                                 ephemeral=True)
                return

            # Add member to the party
            try:
                await self._add(interaction, member, discord_party, job, sheets_party)
            except Exception as e:
                await self._send(interaction, str(e), ephemeral=True)
                return

            # Add/remove from fill party based on joined party status
            fill_party_id = self.sheets_bossing.bosses_dict[sheets_party.boss_name].difficulties[
                sheets_party.difficulty].fill_role_id
            if fill_party_id:  # Fill party exists

                if (sheets_party.status == SheetsParty.PartyStatus.new or
                        sheets_party.status == SheetsParty.PartyStatus.lfg):
                    # Added party status is New or LFG. Add to fill
                    discord_fill_party = interaction.guild.get_role(int(fill_party_id))
                    try:
                        sheets_fill_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                                 sheets_party.role_id == fill_party_id)
                        await self._add(interaction, member, discord_fill_party, job, sheets_fill_party, silent=True)
                    except StopIteration:
                        await self._send(interaction,
                                         f'Warning - Unable to find party {discord_party.mention} in the bossing parties data.',
                                         ephemeral=True)
                    except UserWarning:
                        # Member already has the fill role
                        pass

                elif (sheets_party.status == SheetsParty.PartyStatus.open or
                      sheets_party.status == SheetsParty.PartyStatus.exclusive):
                    # Added party status is Open or Exclusive. Remove from fill
                    discord_fill_party = interaction.guild.get_role(int(fill_party_id))
                    try:
                        sheets_fill_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                                 sheets_party.role_id == fill_party_id)
                        await self._remove(interaction, member, discord_fill_party, job, sheets_fill_party, silent=True)
                    except StopIteration:
                        await self._send(interaction,
                                         f'Warning - Unable to find party {discord_party.mention} in the bossing parties data.',
                                         ephemeral=True)
                    except UserWarning:
                        # Member did not have the fill role
                        pass

            # Remove from LFG party if added to a new, open, or exclusive party
            if (sheets_party.status == SheetsParty.PartyStatus.new or
                    sheets_party.status == SheetsParty.PartyStatus.open or
                    sheets_party.status == SheetsParty.PartyStatus.exclusive):
                lfg_party_id = self.sheets_bossing.bosses_dict[sheets_party.boss_name].difficulties[
                    sheets_party.difficulty].lfg_role_id
                if lfg_party_id != '':
                    discord_lfg_party = interaction.guild.get_role(int(lfg_party_id))
                    try:
                        sheets_lfg_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                                sheets_party.role_id == lfg_party_id)
                        await self._remove(interaction, member, discord_lfg_party, job, sheets_lfg_party)
                    except StopIteration:
                        await self._send(interaction,
                                         f'Warning - Unable to find party {discord_party.mention} in the bossing parties data.',
                                         ephemeral=True)
                    except UserWarning:
                        # Member did not have the LFG role
                        pass

    async def _add(self, interaction, member, discord_party, job, sheets_party: SheetsParty, silent=False):
        if sheets_party.status == SheetsParty.PartyStatus.retired:
            raise Exception(f'Error - {discord_party.mention} is retired.')

        # Check if the party is already full
        if sheets_party.status != SheetsParty.PartyStatus.lfg and sheets_party.status != SheetsParty.PartyStatus.fill and int(
                sheets_party.member_count) == int(sheets_party.max_member_count):
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
        self._update_existing_party(discord_party)

        # Success
        added_message = f'Added {member.mention} *{job}* to {discord_party.mention}'
        if sheets_party.party_thread_id:
            added_message += f' <#{sheets_party.party_thread_id}>'
        elif sheets_party.status == SheetsParty.PartyStatus.lfg or sheets_party.status == SheetsParty.PartyStatus.fill:
            added_message += f' <#{self.sheets_bossing.bosses_dict[sheets_party.boss_name].sign_up_thread_id}>'
        await self._send(interaction, added_message, ephemeral=True, log=True)

        if sheets_party.boss_list_message_id:
            # Update bossing list message
            bossing_parties_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_BOSSING_PARTIES)
            message = await bossing_parties_channel.fetch_message(sheets_party.boss_list_message_id)
            await self.update_boss_party_list_message(message, sheets_party)

        if not silent:
            if sheets_party.party_thread_id:
                # Update thread title, message, and send update in party thread
                party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                message_content = f'{member.mention} *{job}* has been added to {discord_party.mention}.\n\n'
                message_content += self.__get_boss_party_list_message(sheets_party, self.sheets_bossing.members_dict[
                    sheets_party.role_id])
                await party_thread.send(message_content)
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self._update_thread(party_thread, party_message, sheets_party)
            else:
                # Send LFG and Fill updates in Sign Up thread
                sign_up_thread = self.client.get_channel(
                    int(self.sheets_bossing.bosses_dict[sheets_party.boss_name].sign_up_thread_id))
                if sheets_party.status == SheetsParty.PartyStatus.lfg:
                    # Mention role
                    message_content = f'{member.mention} *{job}* has been added to {discord_party.mention}.\n\n'
                    message_content += self.__get_boss_party_list_message(sheets_party,
                                                                          self.sheets_bossing.members_dict[
                                                                              sheets_party.role_id])
                    await sign_up_thread.send(message_content)
                elif sheets_party.status == SheetsParty.PartyStatus.fill:
                    # Do not mention role
                    await sign_up_thread.send(
                        f'{member.mention} *{job}* has been added to {sheets_party.difficulty}{sheets_party.boss_name} Fill.')

    async def remove(self, interaction, member, discord_party, job=''):
        # Validate that this is a bossing party role
        try:
            sheets_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                sheets_party.role_id == str(discord_party.id))
        except StopIteration:
            await self._send(interaction,
                             f'Error - Unable to find party {discord_party.id} in the bossing parties data.',
                             ephemeral=True)
            return

        async with self.lock:
            # Remove member from party
            try:
                removed_sheets_member = await self._remove(interaction, member, discord_party, job, sheets_party)
            except Exception as e:
                await self._send(interaction, str(e), ephemeral=True)
                return

            # Remove from fill if the party is new or LFG
            fill_party_id = self.sheets_bossing.bosses_dict[sheets_party.boss_name].difficulties[
                sheets_party.difficulty].fill_role_id
            if fill_party_id:  # Fill party exists
                if (sheets_party.status == SheetsParty.PartyStatus.new or
                        sheets_party.status == SheetsParty.PartyStatus.lfg):
                    # Removed party status is New or LFG. Remove from fill
                    discord_fill_party = interaction.guild.get_role(int(fill_party_id))
                    try:
                        sheets_fill_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                                 sheets_party.role_id == fill_party_id)
                        await self._remove(interaction, member, discord_fill_party, removed_sheets_member.job,
                                           sheets_fill_party, silent=True)
                    except StopIteration:
                        await self._send(interaction,
                                         f'Warning - Unable to find party {discord_party.mention} in the bossing parties data.',
                                         ephemeral=True)
                    except UserWarning:
                        # Member did not have the fill role
                        pass

    async def _remove(self, interaction, member, discord_party, job, sheets_party, silent=False, left_server=False):
        if not left_server:
            # Check if user has the role
            try:
                next(discord_member for discord_member in discord_party.members if discord_member.id == member.id)
            except StopIteration:
                raise UserWarning(f'Error - {member.mention} is not in {discord_party.mention}.')

        if (sheets_party.status != SheetsParty.PartyStatus.lfg and
                sheets_party.status != SheetsParty.PartyStatus.fill and
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
        self._update_existing_party(discord_party)

        # Success
        removed_message = f'Removed {member.mention} *{removed_sheets_member.job}* from {discord_party.mention}'
        if sheets_party.party_thread_id:
            removed_message += f' <#{sheets_party.party_thread_id}>'
        elif sheets_party.status == SheetsParty.PartyStatus.lfg or sheets_party.status == SheetsParty.PartyStatus.fill:
            removed_message += f' <#{self.sheets_bossing.bosses_dict[sheets_party.boss_name].sign_up_thread_id}>'
        await self._send(interaction, removed_message, ephemeral=True, log=True)

        if sheets_party.boss_list_message_id:
            # Update bossing list message
            bossing_parties_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_BOSSING_PARTIES)
            message = await bossing_parties_channel.fetch_message(sheets_party.boss_list_message_id)
            await self.update_boss_party_list_message(message, sheets_party)

        if not silent:
            if sheets_party.party_thread_id:
                # Update thread title, message, and send update in party thread
                party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                message_content = f'{member.mention} *{removed_sheets_member.job}* has been removed from {discord_party.mention}.\n\n'
                message_content += self.__get_boss_party_list_message(sheets_party, self.sheets_bossing.members_dict[
                    sheets_party.role_id])
                await party_thread.send(message_content)
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self._update_thread(party_thread, party_message, sheets_party)
            else:
                # Send LFG and Fill updates in Sign Up thread
                sign_up_thread = self.client.get_channel(
                    int(self.sheets_bossing.bosses_dict[sheets_party.boss_name].sign_up_thread_id))
                # Do not mention role
                await sign_up_thread.send(
                    f'{member.mention} *{removed_sheets_member.job}* has been removed from {discord_party.name}.')

        return removed_sheets_member

    async def new(self, interaction, boss_name, difficulty):
        if boss_name not in self.sheets_bossing.get_boss_names():
            await self._send(interaction,
                             f'Error - `{boss_name}` is not a valid bossing name. Valid bossing names are as follows:\n'
                             f'`{reduce(lambda acc, val: acc + (", " if acc else "") + val, self.sheets_bossing.get_boss_names())}`',
                             ephemeral=True)
            return

        if len(self.sheets_bossing.bosses_dict[boss_name].difficulties) > 1:
            if difficulty == "":
                await self._send(interaction,
                                 f'Error - `{boss_name}` requires a difficulty. Valid difficulties for `{boss_name}` are as follows:\n'
                                 f'`{reduce(lambda acc, val: acc + (", " if acc else "") + val, self.sheets_bossing.bosses_dict[boss_name].difficulties.keys())}`',
                                 ephemeral=True)
                return
            elif difficulty not in self.sheets_bossing.bosses_dict[boss_name].difficulties.keys():
                await self._send(interaction,
                                 f'Error - `{difficulty}` is not a valid difficulty for `{boss_name}`. Valid difficulties are as follows:\n'
                                 f'`{reduce(lambda acc, val: acc + (", " if acc else "") + val, self.sheets_bossing.bosses_dict[boss_name].difficulties.keys())}`',
                                 ephemeral=True)
                return
        elif difficulty != "" and len(self.sheets_bossing.bosses_dict[boss_name].difficulties) == 1:
            await self._send(interaction,
                             f'Error - `{boss_name}` does not support multiple difficulties.',
                             ephemeral=True)
            return

        max_member_count = self.sheets_bossing.bosses_dict[boss_name].difficulties[difficulty].max_member_count

        async with self.lock:
            new_party_boss_index = self.sheets_bossing.get_boss_names().index(boss_name)
            sheets_parties: list[SheetsParty] = self.sheets_bossing.parties
            sheets_parties_index = 0
            party_number = 1
            new_sheets_party = None
            for sheets_party in sheets_parties:
                party_boss_index = self.sheets_bossing.get_boss_names().index(sheets_party.boss_name)
                if party_boss_index == new_party_boss_index:
                    # Found LFG or Fill party for the corresponding bossing, insert new party above it
                    if sheets_party.party_number == 'LFG' or sheets_party.party_number == 'Fill':
                        new_boss_party = await interaction.guild.create_role(
                            name=f'{difficulty}{boss_name} Party {party_number}',
                            colour=self.sheets_bossing.bosses_dict[
                                boss_name].get_role_colour(),
                            mentionable=True)
                        await new_boss_party.edit(
                            position=interaction.guild.get_role(int(sheets_party.role_id)).position)
                        new_sheets_party = SheetsParty.new_party(new_boss_party.id, boss_name, difficulty, party_number,
                                                                 max_member_count)
                        sheets_parties.insert(sheets_parties_index, new_sheets_party)
                        break
                    else:
                        party_number += 1

                elif party_boss_index > new_party_boss_index:
                    # Found a party bossing that comes after, insert new party above it
                    new_boss_party = await interaction.guild.create_role(
                        name=f'{difficulty}{boss_name} Party {party_number}',
                        colour=self.sheets_bossing.bosses_dict[
                            boss_name].get_role_colour(),
                        mentionable=True)
                    await new_boss_party.edit(
                        position=interaction.guild.get_role(int(sheets_party.role_id)).position)
                    new_sheets_party = SheetsParty.new_party(new_boss_party.id, boss_name, difficulty, party_number,
                                                             max_member_count)
                    sheets_parties.insert(sheets_parties_index, new_sheets_party)
                    break

                sheets_parties_index += 1

            if new_sheets_party is None:
                # Couldn't find any of the above, new party must come last
                new_boss_party = await interaction.guild.create_role(
                    name=f'{difficulty}{boss_name} Party {party_number}',
                    colour=self.sheets_bossing.bosses_dict[
                        boss_name].get_role_colour(), mentionable=True)
                await new_boss_party.edit(
                    position=interaction.guild.get_role(int(sheets_parties[-1].role_id)).position - 1)
                new_sheets_party = SheetsParty.new_party(new_boss_party.id, boss_name, difficulty, party_number,
                                                         max_member_count)
                sheets_parties.append(new_sheets_party)

            # Update spreadsheet
            self.sheets_bossing.update_parties(sheets_parties, [new_sheets_party])

            # Create thread
            boss_forum = self.client.get_channel(int(self.sheets_bossing.bosses_dict[boss_name].forum_channel_id))
            party_thread_with_message = await boss_forum.create_thread(
                name=f'{new_sheets_party.difficulty}{new_sheets_party.boss_name} Party {new_sheets_party.party_number} - New',
                content=f'{new_boss_party.mention}')
            sheets_parties = self.sheets_bossing.parties
            for sheets_party in sheets_parties:
                if sheets_party.role_id == str(new_boss_party.id):
                    sheets_party.party_thread_id = str(party_thread_with_message.thread.id)
                    sheets_party.party_message_id = str(party_thread_with_message.message.id)
                    break
            self.sheets_bossing.update_parties(sheets_parties)

            await self._send(interaction,
                             f'Created {new_boss_party.name} {party_thread_with_message.thread.mention}',
                             ephemeral=True, log=True)

            # Remake bossing party list
            await self.__remake_boss_party_list(interaction)

    async def mod_set_recurring_time(self, interaction, discord_party, weekday_str, hour, minute):
        sheets_parties = self.sheets_bossing.parties
        try:
            sheets_party = next(
                sheets_party for sheets_party in sheets_parties if sheets_party.role_id == str(discord_party.id))
        except StopIteration:
            await self._send(interaction,
                             f'Error - Unable to find party {discord_party.mention} in the bossing parties data.',
                             ephemeral=True)
            return

        await self._send(interaction, f'<#{sheets_party.party_thread_id}>', ephemeral=True)
        await self.__set_recurring_time(interaction, sheets_party, weekday_str, hour, minute)

    async def user_set_recurring_time(self, interaction: discord.Interaction, weekday_str, hour, minute):
        # Get boss party role associated with the thread this command was sent from
        try:
            sheets_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                sheets_party.party_thread_id == str(interaction.channel_id))
        except StopIteration:
            await self._send(interaction,
                             f'Error - This command can only be used in a boss party thread.',
                             ephemeral=True)
            return

        try:
            next(
                sheets_member for sheets_member in self.sheets_bossing.members_dict[sheets_party.role_id] if
                sheets_member.user_id == str(interaction.user.id))
            await self.__set_recurring_time(interaction, sheets_party, weekday_str, hour, minute)
        except StopIteration:
            await interaction.followup.send(f'Error - You are not in <@&{sheets_party.role_id}>.')

    async def __set_recurring_time(self, interaction, sheets_party: SheetsParty, weekday_str, hour, minute):
        if sheets_party.status == SheetsParty.PartyStatus.retired:
            await self._send(interaction, f'Error - <@&{sheets_party.role_id}> is retired.', ephemeral=True)
            return

        if sheets_party.status == SheetsParty.PartyStatus.lfg or sheets_party.status == SheetsParty.PartyStatus.fill:
            await self._send(interaction, f'Error - <@&{sheets_party.role_id}> is not a party.',
                             ephemeral=True)
            return

        try:
            weekday = SheetsParty.Weekday[weekday_str.lower()]
        except KeyError:
            await self._send(interaction,
                             'Error - Invalid weekday. Valid input values: [ mon | tue | wed | thu | fri | sat | sun ]',
                             ephemeral=True)
            return

        if hour < 0 or hour > 23:
            await self._send(interaction, 'Error - Invalid hour. Hour must be from 0-23.', ephemeral=True)
            return

        if minute < 0 or minute > 59:
            await self._send(interaction, 'Error - Invalid minute. Minute must be from 0-59.', ephemeral=True)
            return

        # Confirmation
        timestamp = SheetsParty.next_party_recurring_time(weekday.value, hour, minute)
        confirmation_message = f'Please confirm the following new recurring time: <t:{timestamp}:F>'

        class Buttons(discord.ui.View):
            def __init__(self, *, timeout=180):
                super().__init__(timeout=timeout)
                self.message = None
                self.interacted = False

            async def on_timeout(self) -> None:
                if not self.interacted:
                    await self.message.edit(view=None)
                    await interaction.followup.send('Error - Your command has timed out.', ephemeral=True)

            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
            async def green_button(_self, button_interaction: discord.Interaction, button: discord.ui.Button):
                _self.interacted = True
                await button_interaction.response.edit_message(view=None)
                async with self.lock:
                    sheets_parties = self.sheets_bossing.parties

                    sheets_party.weekday = weekday.name
                    sheets_party.hour = str(hour)
                    sheets_party.minute = str(minute)
                    sheets_party.check_in_message_id = ''
                    self.sheets_bossing.update_parties(sheets_parties)
                    self._restart_service()
                    timestamp = sheets_party.next_scheduled_time()

                    if sheets_party.boss_list_message_id:
                        # Update bossing list message
                        bossing_parties_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_BOSSING_PARTIES)
                        message = await bossing_parties_channel.fetch_message(sheets_party.boss_list_message_id)
                        await self.update_boss_party_list_message(message, sheets_party)

                    if sheets_party.party_thread_id:
                        # Update thread title, message, and send update in party thread
                        party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                        if sheets_party.party_message_id:
                            party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                        else:
                            party_message = None
                        await self._update_thread(party_thread, party_message, sheets_party)
                        await party_thread.send(
                            f'<@&{sheets_party.role_id}> time has been updated.\n**Next run:** <t:{timestamp}:F> <t:{timestamp}:R>')

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
            async def red_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                self.interacted = True
                await button_interaction.response.edit_message(view=None)
                await interaction.followup.send(f'<@&{sheets_party.role_id}> set recurring time has been cancelled.',
                                                ephemeral=True)

        buttons_view = Buttons()
        buttons_view.message = await interaction.followup.send(confirmation_message, view=buttons_view, ephemeral=True)

    async def mod_clear_recurring_time(self, interaction, discord_party):
        sheets_parties = self.sheets_bossing.parties
        try:
            sheets_party = next(
                sheets_party for sheets_party in sheets_parties if sheets_party.role_id == str(discord_party.id))
        except StopIteration:
            await self._send(interaction,
                             f'Error - Unable to find party {discord_party.mention} in the bossing parties data.',
                             ephemeral=True)
            return

        await self._send(interaction, f'<#{sheets_party.party_thread_id}>', ephemeral=True)
        await self.__clear_recurring_time(interaction, sheets_party)

    async def user_clear_recurring_time(self, interaction: discord.Interaction):
        # Get boss party role associated with the thread this command was sent from
        try:
            sheets_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                sheets_party.party_thread_id == str(interaction.channel_id))
        except StopIteration:
            await self._send(interaction,
                             f'Error - This command can only be used in a boss party thread.',
                             ephemeral=True)
            return

        try:
            next(sheets_member for sheets_member in self.sheets_bossing.members_dict[sheets_party.role_id] if
                 sheets_member.user_id == str(interaction.user.id))
            await self.__clear_recurring_time(interaction, sheets_party)
        except StopIteration:
            await interaction.followup.send(f'Error - You are not in <@&{sheets_party.role_id}>.')

    async def __clear_recurring_time(self, interaction, sheets_party: SheetsParty):
        async with self.lock:
            sheets_parties = self.sheets_bossing.parties

            if sheets_party.status == SheetsParty.PartyStatus.retired:
                await self._send(interaction, f'Error - <@&{sheets_party.role_id}> is retired.')
                return

            if sheets_party.status == SheetsParty.PartyStatus.lfg or sheets_party.status == SheetsParty.PartyStatus.fill:
                await self._send(interaction, f'Error - <@&{sheets_party.role_id}> is not a party.')
                return

            sheets_party.weekday = ''
            sheets_party.hour = ''
            sheets_party.minute = ''
            sheets_party.check_in_message_id = ''
            self.sheets_bossing.update_parties(sheets_parties)
            self._restart_service()

            if sheets_party.boss_list_message_id:
                # Update bossing list message
                bossing_parties_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_BOSSING_PARTIES)
                message = await bossing_parties_channel.fetch_message(sheets_party.boss_list_message_id)
                await self.update_boss_party_list_message(message, sheets_party)

            if sheets_party.party_thread_id:
                # Update thread title, message, and send update in party thread
                party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self._update_thread(party_thread, party_message, sheets_party)
                message_content = f'<@&{sheets_party.role_id}> recurring time has been cleared.'
                timestamp = sheets_party.next_scheduled_time()
                if timestamp:
                    message_content += f'Next run: <t:{timestamp}:F>'
                await party_thread.send(message_content)

    async def mod_set_one_time(self, interaction, discord_party, timestamp: int):
        sheets_parties = self.sheets_bossing.parties
        try:
            sheets_party = next(
                sheets_party for sheets_party in sheets_parties if sheets_party.role_id == str(discord_party.id))
        except StopIteration:
            await self._send(interaction,
                             f'Error - Unable to find party {discord_party.mention} in the bossing parties data.',
                             ephemeral=True)
            return

        await self._send(interaction, f'<#{sheets_party.party_thread_id}>', ephemeral=True)
        await self.__set_one_time(interaction, sheets_party, timestamp)

    async def user_set_one_time(self, interaction: discord.Interaction, timestamp):
        # Get boss party role associated with the thread this command was sent from
        try:
            sheets_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                sheets_party.party_thread_id == str(interaction.channel_id))
        except StopIteration:
            await self._send(interaction,
                             f'Error - This command can only be used in a boss party thread.',
                             ephemeral=True)
            return

        try:
            next(
                sheets_member for sheets_member in self.sheets_bossing.members_dict[sheets_party.role_id] if
                sheets_member.user_id == str(interaction.user.id))
            await self.__set_one_time(interaction, sheets_party, timestamp)
        except StopIteration:
            await interaction.followup.send(f'Error - You are not in <@&{sheets_party.role_id}>.')

    async def __set_one_time(self, interaction, sheets_party: SheetsParty, one_time_timestamp: int):
        if sheets_party.status == SheetsParty.PartyStatus.retired:
            await self._send(interaction, f'Error - <@&{sheets_party.role_id}> is retired.', ephemeral=True)
            return

        if sheets_party.status == SheetsParty.PartyStatus.lfg or sheets_party.status == SheetsParty.PartyStatus.fill:
            await self._send(interaction, f'Error - <@&{sheets_party.role_id}> is not a party.',
                             ephemeral=True)
            return

        now = int(datetime.timestamp(datetime.now()))
        if one_time_timestamp < now:
            await self._send(interaction, f'Error - <t:{one_time_timestamp}:F> is in the past.'
                                          f'\nhttps://www.unixtimestamp.com/', ephemeral=True)
            return

        # Confirmation
        confirmation_message = f'Please confirm the following one-time scheduled run: <t:{one_time_timestamp}:F>'
        confirmation_message += f'\nhttps://www.unixtimestamp.com/'

        class Buttons(discord.ui.View):
            def __init__(self, *, timeout=180):
                super().__init__(timeout=timeout)
                self.message = None
                self.interacted = False

            async def on_timeout(self) -> None:
                if not self.interacted:
                    await self.message.edit(view=None)
                    await interaction.followup.send('Error - Your command has timed out.', ephemeral=True)

            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
            async def green_button(_self, button_interaction: discord.Interaction, button: discord.ui.Button):
                _self.interacted = True
                await button_interaction.response.edit_message(view=None)
                async with self.lock:
                    sheets_parties = self.sheets_bossing.parties

                    sheets_party.one_time = str(one_time_timestamp)
                    sheets_party.check_in_message_id = ''
                    self.sheets_bossing.update_parties(sheets_parties)
                    self._restart_service()
                    timestamp = sheets_party.next_scheduled_time()

                    if sheets_party.boss_list_message_id:
                        # Update bossing list message
                        bossing_parties_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_BOSSING_PARTIES)
                        message = await bossing_parties_channel.fetch_message(sheets_party.boss_list_message_id)
                        await self.update_boss_party_list_message(message, sheets_party)

                    if sheets_party.party_thread_id:
                        # Update thread title, message, and send update in party thread
                        party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                        if sheets_party.party_message_id:
                            party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                        else:
                            party_message = None
                        await self._update_thread(party_thread, party_message, sheets_party)
                        await party_thread.send(
                            f'<@&{sheets_party.role_id}> a one-time scheduled run has been set for <t:{one_time_timestamp}:F>.\n**Next run:** <t:{timestamp}:F> <t:{timestamp}:R>')

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
            async def red_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                self.interacted = True
                await button_interaction.response.edit_message(view=None)
                await interaction.followup.send(f'<@&{sheets_party.role_id}> set one-time has been cancelled.',
                                                ephemeral=True)

        buttons_view = Buttons()
        buttons_view.message = await interaction.followup.send(confirmation_message, view=buttons_view, ephemeral=True)

    async def mod_clear_one_time(self, interaction, discord_party):
        sheets_parties = self.sheets_bossing.parties
        try:
            sheets_party = next(
                sheets_party for sheets_party in sheets_parties if sheets_party.role_id == str(discord_party.id))
        except StopIteration:
            await self._send(interaction,
                             f'Error - Unable to find party {discord_party.mention} in the bossing parties data.',
                             ephemeral=True)
            return

        await self._send(interaction, f'<#{sheets_party.party_thread_id}>', ephemeral=True)
        await self.__clear_one_time(interaction, sheets_party)

    async def user_clear_one_time(self, interaction: discord.Interaction):
        # Get boss party role associated with the thread this command was sent from
        try:
            sheets_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                sheets_party.party_thread_id == str(interaction.channel_id))
        except StopIteration:
            await self._send(interaction,
                             f'Error - This command can only be used in a boss party thread.',
                             ephemeral=True)
            return

        try:
            next(sheets_member for sheets_member in self.sheets_bossing.members_dict[sheets_party.role_id] if
                 sheets_member.user_id == str(interaction.user.id))
            await self.__clear_one_time(interaction, sheets_party)
        except StopIteration:
            await interaction.followup.send(f'Error - You are not in <@&{sheets_party.role_id}>.')

    async def __clear_one_time(self, interaction, sheets_party: SheetsParty):
        async with self.lock:
            sheets_parties = self.sheets_bossing.parties

            if sheets_party.status == SheetsParty.PartyStatus.retired:
                await self._send(interaction, f'Error - <@&{sheets_party.role_id}> is retired.')
                return

            if sheets_party.status == SheetsParty.PartyStatus.lfg or sheets_party.status == SheetsParty.PartyStatus.fill:
                await self._send(interaction, f'Error - <@&{sheets_party.role_id}> is not a party.')
                return

            sheets_party.one_time = ''
            sheets_party.check_in_message_id = ''
            self.sheets_bossing.update_parties(sheets_parties)
            self._restart_service()

            if sheets_party.boss_list_message_id:
                # Update bossing list message
                bossing_parties_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_BOSSING_PARTIES)
                message = await bossing_parties_channel.fetch_message(sheets_party.boss_list_message_id)
                await self.update_boss_party_list_message(message, sheets_party)

            if sheets_party.party_thread_id:
                # Update thread title, message, and send update in party thread
                party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self._update_thread(party_thread, party_message, sheets_party)
                message_content = f'<@&{sheets_party.role_id}> one-time scheduled run has been cleared.'
                timestamp = sheets_party.next_scheduled_time()
                if timestamp:
                    message_content += f'\n**Next run:** <t:{timestamp}:F>'
                await party_thread.send(message_content)

    async def user_next_time(self, interaction: discord.Interaction):
        # Get boss party role associated with the thread this command was sent from
        try:
            sheets_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                sheets_party.party_thread_id == str(interaction.channel_id))
        except StopIteration:
            await self._send(interaction,
                             f'Error - This command can only be used in a boss party thread.',
                             ephemeral=True)
            return

        try:
            next(sheets_member for sheets_member in self.sheets_bossing.members_dict[sheets_party.role_id] if
                 sheets_member.user_id == str(interaction.user.id))
            await self.__next_time(interaction, sheets_party)
        except StopIteration:
            await interaction.followup.send(f'Error - You are not in <@&{sheets_party.role_id}>.')

    async def __next_time(self, interaction, sheets_party: SheetsParty):
        async with self.lock:
            sheets_parties = self.sheets_bossing.parties

            if sheets_party.status == SheetsParty.PartyStatus.retired:
                await self._send(interaction, f'Error - <@&{sheets_party.role_id}> is retired.')
                return

            if sheets_party.status == SheetsParty.PartyStatus.lfg or sheets_party.status == SheetsParty.PartyStatus.fill:
                await self._send(interaction, f'Error - <@&{sheets_party.role_id}> is not a party.')
                return

            timestamp = sheets_party.next_scheduled_time()

            message_content = (f'<@&{sheets_party.role_id}>'
                               f'\n**Next run**: <t:{timestamp}:F> <t:{timestamp}:R>')
            await self._send(interaction, message_content)

    async def retire(self, interaction, discord_party):
        # Validate that this is a bossing party role
        try:
            sheets_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                sheets_party.role_id == str(discord_party.id))
        except StopIteration:
            await self._send(interaction, f'Error - {discord_party.mention} is not a bossing party.', ephemeral=True)
            return

        if sheets_party.status == SheetsParty.PartyStatus.retired:
            await self._send(interaction, f'Error - {discord_party.mention} is already retired.', ephemeral=True)
            return

        if sheets_party.status == SheetsParty.PartyStatus.new:
            await self._send(interaction, f'Error - {discord_party.mention} is new, you cannot retire a new party.',
                             ephemeral=True)
            return

        if (sheets_party.status == SheetsParty.PartyStatus.lfg or
                sheets_party.status == SheetsParty.PartyStatus.fill):
            await self._send(interaction, f'Error - {discord_party.mention} is not a bossing party.', ephemeral=True)
            return

        # Confirmation
        confirmation_message = f'Are you sure you want to retire {discord_party.mention}? The following {len(discord_party.members)} member(s) will be removed from the party:\n'
        for member in discord_party.members:
            confirmation_message += f'{member.mention}\n'

        class Buttons(discord.ui.View):
            def __init__(self, *, timeout=180):
                super().__init__(timeout=timeout)
                self.message = None
                self.interacted = False

            async def on_timeout(self) -> None:
                if not self.interacted:
                    await self.message.edit(view=None)
                    await interaction.followup.send('Error - Your command has timed out.', ephemeral=True)

            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
            async def green_button(_self, button_interaction: discord.Interaction, button: discord.ui.Button):
                _self.interacted = True
                await button_interaction.response.edit_message(view=None)
                async with self.lock:
                    # Remove members from party
                    for member in discord_party.members:
                        await self._remove(interaction, member, discord_party, '', sheets_party, silent=True)

                    # Update party status to retired
                    updated_discord_party = await discord_party.edit(name=f'{discord_party.name} (Retired)',
                                                                     mentionable=False)

                    # Delete bossing party list messages
                    bossing_parties_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_BOSSING_PARTIES)
                    if sheets_party.boss_list_message_id:
                        message = await bossing_parties_channel.fetch_message(sheets_party.boss_list_message_id)
                        await message.delete()
                    if sheets_party.boss_list_decorator_id:
                        message = await bossing_parties_channel.fetch_message(sheets_party.boss_list_decorator_id)
                        await message.delete()

                    self._update_existing_party(updated_discord_party)
                    self._restart_service()

                    if sheets_party.party_thread_id:
                        # Update thread title, message, and send update in party thread
                        party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                        if sheets_party.party_message_id:
                            party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                        else:
                            party_message = None
                        await self._update_thread(party_thread, party_message, sheets_party)

                await self._send(interaction, f'{updated_discord_party.mention} has been retired.', ephemeral=True,
                                 log=True)

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
            async def red_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                self.interacted = True
                await button_interaction.response.edit_message(view=None)
                await interaction.followup.send(f'Retiring of {discord_party.mention} has been cancelled.',
                                                ephemeral=True)

        buttons_view = Buttons()
        buttons_view.message = await interaction.followup.send(confirmation_message, view=buttons_view, ephemeral=True)

    async def exclusive(self, interaction, discord_party):
        await self.__update_active_status(interaction, discord_party, SheetsParty.PartyStatus.exclusive)

    async def open(self, interaction, discord_party):
        await self.__update_active_status(interaction, discord_party, SheetsParty.PartyStatus.open)

    async def __update_active_status(self, interaction, discord_party, status):
        async with self.lock:
            sheets_parties = self.sheets_bossing.parties
            try:
                sheets_party = next(
                    sheets_party for sheets_party in sheets_parties if sheets_party.role_id == str(discord_party.id))
            except StopIteration:
                await self._send(interaction, f'Error - {discord_party.mention} is not a bossing party.',
                                 ephemeral=True)
                return

            if sheets_party.status == SheetsParty.PartyStatus.retired:
                await self._send(interaction, f'Error - {discord_party.mention} is retired and cannot be reopened.',
                                 ephemeral=True)
                return

            if sheets_party.status == status:
                await self._send(interaction, f'Error - {discord_party.mention} is already {status.value}.',
                                 ephemeral=True)
                return

            if status != SheetsParty.PartyStatus.exclusive and status != SheetsParty.PartyStatus.open:
                await self._send(interaction, f'Error - {discord_party.mention} cannot be {status.value}.',
                                 ephemeral=True)

            if sheets_party.status == SheetsParty.PartyStatus.new:
                # Remove fill roles of members if changing status from new
                fill_party_id = self.sheets_bossing.bosses_dict[sheets_party.boss_name].difficulties[
                    sheets_party.difficulty].fill_role_id
                if fill_party_id:  # Fill party exists
                    discord_fill_party = interaction.guild.get_role(int(fill_party_id))
                    try:
                        sheets_fill_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                                 sheets_party.role_id == fill_party_id)

                        for discord_member in discord_party.members:
                            try:
                                sheets_member = next(
                                    sheets_member for sheets_member in self.sheets_bossing.members_dict[fill_party_id]
                                    if sheets_member.user_id == str(discord_member.id))
                                try:
                                    await self._remove(interaction, discord_member, discord_fill_party,
                                                       sheets_member.job,
                                                       sheets_fill_party, silent=True)
                                except Exception as e:
                                    await self._send(interaction, str(e), ephemeral=True)
                            except StopIteration:
                                # Member not in fill, silently handle exception
                                pass
                    except StopIteration:
                        await self._send(interaction,
                                         f'Error - Unable to find party {discord_party.mention} in the bossing parties data.',
                                         ephemeral=True)

            sheets_party.status = status
            self.sheets_bossing.update_parties(sheets_parties)
            await self._send(interaction, f'{discord_party.name} is now {sheets_party.status.value}.', ephemeral=True,
                             log=True)

            if sheets_party.boss_list_message_id:
                # Update bossing list message
                bossing_parties_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_BOSSING_PARTIES)
                message = await bossing_parties_channel.fetch_message(sheets_party.boss_list_message_id)
                await self.update_boss_party_list_message(message, sheets_party)

            if sheets_party.party_thread_id:
                # Update thread title, message, and send update in party thread
                party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self._update_thread(party_thread, party_message, sheets_party)

    async def difficulty(self, interaction, discord_party: discord.Role, difficulty: str):
        async with self.lock:
            sheets_parties = self.sheets_bossing.parties

            try:
                sheets_party = next(sheets_party for sheets_party in self.sheets_bossing.parties if
                                    sheets_party.role_id == str(discord_party.id))
            except StopIteration:
                await self._send(interaction, f'Error - {discord_party.mention} is not a bossing party.',
                                 ephemeral=True)
                return

            if sheets_party.status == SheetsParty.PartyStatus.retired:
                await self._send(interaction, f'Error - <@&{sheets_party.role_id}> is retired.', ephemeral=True)
                return

            if sheets_party.status == SheetsParty.PartyStatus.lfg or sheets_party.status == SheetsParty.PartyStatus.fill:
                await self._send(interaction, f'Error - <@&{sheets_party.role_id}> is not a party.', ephemeral=True)
                return

            if sheets_party.difficulty == difficulty:
                await self._send(interaction,
                                 f'Error - <@&{sheets_party.role_id}> difficulty is already `{difficulty}`.',
                                 ephemeral=True)
                return

            if len(self.sheets_bossing.bosses_dict[sheets_party.boss_name].difficulties) > 1:
                if difficulty not in self.sheets_bossing.bosses_dict[sheets_party.boss_name].difficulties.keys():
                    await self._send(interaction,
                                     f'Error - `{difficulty}` is not a valid difficulty for `{sheets_party.boss_name}`. Valid difficulties are as follows:\n'
                                     f'`{reduce(lambda acc, val: acc + (", " if acc else "") + val, self.sheets_bossing.bosses_dict[sheets_party.boss_name].difficulties.keys())}`',
                                     ephemeral=True)
                    return
            elif len(self.sheets_bossing.bosses_dict[sheets_party.boss_name].difficulties) == 1:
                await self._send(interaction,
                                 f'Error - `{sheets_party.boss_name}` does not support multiple difficulties.',
                                 ephemeral=True)
                return

            new_max_member_count = self.sheets_bossing.bosses_dict[sheets_party.boss_name].difficulties[
                difficulty].max_member_count
            if int(sheets_party.member_count) > int(new_max_member_count):
                await self._send(interaction,
                                 f'Error - Party member count exceeds `{difficulty}{sheets_party.boss_name}` max member count of {new_max_member_count}.',
                                 ephemeral=True)
                return

            # Update party sheet
            sheets_party.difficulty = difficulty
            sheets_party.max_member_count = new_max_member_count
            # Update role name
            discord_party = await discord_party.edit(
                name=f'{sheets_party.difficulty}{sheets_party.boss_name} Party {sheets_party.party_number}')

            self.sheets_bossing.update_parties(sheets_parties)
            await self._send(interaction, f'{discord_party.name} is now {sheets_party.difficulty} difficulty.',
                             ephemeral=True,
                             log=True)

            if sheets_party.party_thread_id:
                # Update thread title
                party_thread = await self.client.fetch_channel(int(sheets_party.party_thread_id))
                if sheets_party.party_message_id:
                    party_message = await party_thread.fetch_message(sheets_party.party_message_id)
                else:
                    party_message = None
                await self._update_thread(party_thread, party_message, sheets_party)

    async def listremake(self, interaction):
        # Confirmation
        confirmation_message_body = f'Are you sure you want to remake the bossing party list in <#{config.GROVE_CHANNEL_ID_BOSSING_PARTIES}>?\n'
        confirmation_message_body += f'\nReact with 👍 to proceed.'

        confirmation_message = await self._send(interaction, confirmation_message_body)
        await confirmation_message.add_reaction('👍')

        def check(reaction, user):
            print(reaction)
            return user == interaction.user and str(reaction.emoji) == '👍'

        try:
            await self.client.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await self._send(interaction, 'Error - confirmation expired. Party retire has been cancelled.',
                             ephemeral=True)
            return

        async with self.lock:
            await self.__remake_boss_party_list(interaction)

    async def remove_member_from_bossing_parties(self, member: discord.Member, left_server: bool):
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
                                       silent=sheets_party.status == SheetsParty.PartyStatus.fill,
                                       left_server=left_server)
                except Exception as e:
                    await self._send(None, str(e))

    async def __remake_boss_party_list(self, interaction):
        # Delete existing messages
        bossing_parties_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_BOSSING_PARTIES)

        new_sheets_parties = self.sheets_bossing.parties

        await self._send(interaction, 'Deleting the existing bossing party list...', ephemeral=True)
        await bossing_parties_channel.purge(limit=len(new_sheets_parties) * 2)

        try:
            for sheets_party in new_sheets_parties:
                sheets_party.boss_list_message_id = ''
                sheets_party.boss_list_decorator_id = ''
        except IndexError:
            return

        self.sheets_bossing.update_parties(new_sheets_parties)

        await self._send(interaction, 'Existing bossing party list deleted.', ephemeral=True)

        # Send the bossing party messages
        await self._send(interaction, 'Creating the new bossing party list...', ephemeral=True)

        current_sheets_boss = None
        for sheets_party in new_sheets_parties:
            if sheets_party.status == SheetsParty.PartyStatus.retired:
                continue

            # Send section title
            if not current_sheets_boss or current_sheets_boss.boss_name != sheets_party.boss_name:
                current_sheets_boss = self.sheets_bossing.bosses_dict[sheets_party.boss_name]
                section_title_content = (f'_ _'
                                         f'\n# {current_sheets_boss.human_readable_name} <#{current_sheets_boss.sign_up_thread_id}>')
                message = await bossing_parties_channel.send(section_title_content)
                sheets_party.boss_list_decorator_id = str(message.id)
            else:
                message = await bossing_parties_channel.send('_ _')
                sheets_party.boss_list_decorator_id = str(message.id)

            # Placeholder first to avoid mention
            message = await bossing_parties_channel.send(
                f'{sheets_party.difficulty}{sheets_party.boss_name} Party {sheets_party.party_number}')
            sheets_party.boss_list_message_id = str(message.id)

            await self.update_boss_party_list_message(message, sheets_party)

        etiquette_message = ('_ _'
                             '\n# Bossing etiquette'
                             '\n\nWith organized bossing, it is important that all party members are in attendance to ensure a smooth clear. Out of respect for your fellow guildmates, please follow Grove\'s bossing etiquette:'
                             '\n1. Be on time.'
                             '\n2. If you are unable to make bossing run time for the week, let your party know as soon as possible, and organize another time for your party that week.'
                             '\n3. If you are unable to make the bossing run at all for a week, let your party know as soon as possible, and find a fill for your spot.')
        await bossing_parties_channel.send(etiquette_message)

        self.sheets_bossing.update_parties(new_sheets_parties)

        await self._send(interaction, 'New bossing party list complete.', ephemeral=True)

    def __get_boss_parties(self, discord_roles):
        """Returns the subset of Grove bossing party roles from a list of Discord roles."""
        # get all bossing party roles by matching their names to the bosses
        sheets_parties = self.sheets_bossing.parties
        parties = []
        for role in discord_roles:
            if role.name.find('Party') == -1 and role.name.find('LFG') == -1 and role.name.find('Fill') == -1:
                continue

            for sheets_party in sheets_parties:
                if (sheets_party.party_number == 'LFG' and role.name == f'{sheets_party.boss_name} LFG' or
                        sheets_party.party_number == 'Fill' and role.name == f'{sheets_party.boss_name} Fill' or
                        role.name == f'{sheets_party.difficulty}{sheets_party.boss_name} Party {sheets_party.party_number}'):
                    parties.append(role)
                    break

        return parties

    def _update_existing_party(self, discord_party):
        # Update party status and member count
        new_sheets_parties = self.sheets_bossing.parties
        for sheets_party in new_sheets_parties:
            if sheets_party.role_id == str(discord_party.id):  # Found the existing party we want to update
                sheets_party.member_count = str(len(self.sheets_bossing.members_dict[sheets_party.role_id]))
                if discord_party.name.find('Retired') != -1:
                    # Update to retired
                    sheets_party.status = SheetsParty.PartyStatus.retired
                    sheets_party.weekday = ''
                    sheets_party.hour = ''
                    sheets_party.minute = ''
                    sheets_party.boss_list_message_id = ''
                    sheets_party.boss_list_decorator_id = ''
                break

        self.sheets_bossing.update_parties(new_sheets_parties)

    async def update_boss_party_list_message(self, message: discord.Message, sheets_party: SheetsParty):
        party_sheets_members = self.sheets_bossing.members_dict[sheets_party.role_id]
        message_content = self.__get_boss_party_list_message(sheets_party, party_sheets_members)
        await message.edit(content=message_content)

    @staticmethod
    def __get_boss_party_list_message(sheets_party, party_sheets_members):
        message_content = f'<@&{sheets_party.role_id}>'
        if sheets_party.party_thread_id:
            message_content += f' <#{sheets_party.party_thread_id}>'
        message_content += '\n'
        timestamp = sheets_party.next_scheduled_time()
        if timestamp:
            message_content += f'**Next run:** <t:{timestamp}:F> <t:{timestamp}:R>\n'
        for sheets_member in party_sheets_members:
            message_content += f'<@{sheets_member.user_id}> *{sheets_member.job}*\n'
        if sheets_party.status == SheetsParty.PartyStatus.open or sheets_party.status == SheetsParty.PartyStatus.new:
            for n in range(0, int(sheets_party.max_member_count) - int(sheets_party.member_count)):
                message_content += 'Open\n'
        elif sheets_party.status == SheetsParty.PartyStatus.lfg and len(party_sheets_members) == 0:
            message_content += '*No members looking for group at this time*'
        elif sheets_party.status == SheetsParty.PartyStatus.fill and len(party_sheets_members) == 0:
            message_content += '*No members available to fill at this time*'
        return message_content

    @staticmethod
    async def _update_thread(party_thread: discord.Thread, party_message: discord.Message, sheets_party: SheetsParty):
        # Open and unlock thread
        await party_thread.edit(archived=False, locked=False)

        # Update thread title
        title = f'{sheets_party.difficulty}{sheets_party.boss_name} Party {sheets_party.party_number} - '
        if sheets_party.status == SheetsParty.PartyStatus.retired:
            if party_message:
                message = f'<@&{sheets_party.role_id}>'
                await party_message.edit(content=message)
            title += 'Retired'

            await party_thread.edit(name=title, locked=True)
            await party_thread.edit(archived=True)
        else:
            if sheets_party.status == SheetsParty.PartyStatus.new:
                title += 'New'
            elif sheets_party.status == SheetsParty.PartyStatus.exclusive or sheets_party.status == SheetsParty.PartyStatus.open and sheets_party.member_count == sheets_party.max_member_count:
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

    async def _send(self, interaction, content, ephemeral=False, suppress_embeds=False, log=False):
        if interaction:
            return await interaction.followup.send(content=content, ephemeral=ephemeral,
                                                   suppress_embeds=suppress_embeds)
        if log:
            # Send to log channel
            member_activity_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_MEMBER_ACTIVITY)
            await member_activity_channel.send(content)
