from datetime import datetime, timezone, timedelta

import discord

import config
from absence.service import AbsenceService
from absence.sheets import Absence as SheetsAbsence
from absence.sheets import AbsenceSheets
from bossing.sheets import BossingSheets, Party


class Absence:
    ONE_DAY_IN_SECONDS = 86400

    def __init__(self, client):
        self.client = client
        self.sheets_bossing = BossingSheets()
        self.sheets_absence = AbsenceSheets()

        async def on_start_absence(sheets_absence: SheetsAbsence):
            # Set the Away role
            member = self.client.get_guild(config.GROVE_GUILD_ID).get_member(sheets_absence.user_id)
            if member:
                await member.add_roles(self.client.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_AWAY))

                # Send to log channel
                member_activity_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_MEMBER_ACTIVITY)
                await member_activity_channel.send(
                    f'{member.mention} is now away until <t:{sheets_absence.end}:F>, returning <t:{sheets_absence.end}:R>.')

                # Send to bossing party threads
                member_parties = []
                for sheet_party in self.sheets_bossing.parties:
                    if (sheet_party.status == Party.PartyStatus.new
                            or sheet_party.status == Party.PartyStatus.open
                            or sheet_party.status == Party.PartyStatus.exclusive):
                        for party_member in self.sheets_bossing.members_dict[sheet_party.role_id]:
                            if party_member.user_id == str(member.id):
                                member_parties.append(sheet_party)
                                break

                for member_party in member_parties:
                    party_thread = await self.client.fetch_channel(int(member_party.party_thread_id))
                    message = f'<@&{member_party.role_id}>\n\n'
                    message += f'{member.mention} is now away until <t:{sheets_absence.end}:F>, returning <t:{sheets_absence.end}:R>.'
                    await party_thread.send(message)
            # Delete the absence event
            self.sheets_absence.delete_absence(sheets_absence)

        async def on_end_absence(sheets_absence: SheetsAbsence):
            # Clear the Away role
            member = self.client.get_guild(config.GROVE_GUILD_ID).get_member(sheets_absence.user_id)
            if member:
                await member.remove_roles(
                    self.client.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_AWAY))
            # Delete the absence event
            self.sheets_absence.delete_absence(sheets_absence)

        self.absence_service = AbsenceService(on_start_absence, on_end_absence)

    def _restart_service(self):
        self.absence_service.restart_service(self.sheets_absence.absences)

    def on_ready(self):
        self._restart_service()

    def on_member_remove(self, member: discord.Member):
        deleted_sheets_absences = self.sheets_absence.delete_user_absences(member.id)
        if len(deleted_sheets_absences) > 0:
            self._restart_service()

    async def schedule(self, interaction: discord.Interaction, start_date_str: str, start_reset_offset: float,
                       end_date_str: str,
                       end_reset_offset: float):
        try:
            next(sheets_absence for sheets_absence in self.sheets_absence.absences if
                 sheets_absence.user_id == str(interaction.user.id))
            # Absence already exists
            await interaction.followup.send(
                f'Error - You already have an absence scheduled, you must clear your existing absence before setting a new one.',
                ephemeral=True)
            return
        except StopIteration:
            pass

        now = datetime.now()

        try:
            start_date = datetime.strptime(start_date_str, '%y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            await interaction.followup.send(
                f'Error - start_date parameter must be in the format YYYY-MM-DD, e.g. September 21, 2023 as 2023-09-21.',
                ephemeral=True)
            return
        start_date = start_date + timedelta(hours=start_reset_offset)

        days_in_advance = (start_date.timestamp() - now.timestamp()) / Absence.ONE_DAY_IN_SECONDS
        if days_in_advance > 28:
            await interaction.followup.send(
                f'Error - You cannot schedule an absence more than 28 days in advance.',
                ephemeral=True)
            return

        try:
            end_date = datetime.strptime(end_date_str, '%y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            await interaction.followup.send(
                f'Error - end_date parameter must be in the format YYYY-MM-DD, e.g. September 21, 2023 as 2023-09-21.')
            return
        end_date = end_date + timedelta(hours=end_reset_offset)

        if end_date.timestamp() - now.timestamp() < 0:
            await interaction.followup.send(
                f'Error - Absence cannot be in the past.')
            return

        duration = (end_date.timestamp() - start_date.timestamp()) / Absence.ONE_DAY_IN_SECONDS
        if duration < 0:
            await interaction.followup.send(
                f'Error - Absence cannot end before it starts.')
            return

        member_parties = []
        for sheet_party in self.sheets_bossing.parties:
            if (sheet_party.status == Party.PartyStatus.new
                    or sheet_party.status == Party.PartyStatus.open
                    or sheet_party.status == Party.PartyStatus.exclusive):
                for member in self.sheets_bossing.members_dict[sheet_party.role_id]:
                    if member.user_id == str(interaction.user.id):
                        member_parties.append(sheet_party)
                        break

        message = f'**Start:** <t:{int(start_date.timestamp())}:F> <t:{int(start_date.timestamp())}:R>\n'
        message += f'**End:** <t:{int(end_date.timestamp())}:F> <t:{int(end_date.timestamp())}:R>\n'
        if duration == 1:
            message += f'**Duration:** 1 day\n\n'
        else:
            message += f'**Duration:** {duration:0,.1f} days\n\n'
        message += f'**Bossing parties**\n'
        for member_party in member_parties:
            message += f'<@&{member_party.role_id}>: <#{member_party.party_thread_id}>\n'
        message += f'\nBy submitting this absence request, you confirm that:\n1. All bossing parties have been informed of your upcoming absence.\n2. Fills have been found in all parties where your attendance is required to reliably clear.'

        class Buttons(discord.ui.View):
            def __init__(self, *, timeout=180):
                super().__init__(timeout=timeout)

            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
            async def green_button(_self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.edit_message(view=None)
                start_sheets_absence = SheetsAbsence(int(start_date.timestamp()),
                                                     interaction.user.id,
                                                     SheetsAbsence.Type.start.value,
                                                     int(start_date.timestamp()),
                                                     int(end_date.timestamp()))
                end_sheets_absence = SheetsAbsence(int(end_date.timestamp()),
                                                   interaction.user.id,
                                                   SheetsAbsence.Type.end.value,
                                                   int(start_date.timestamp()),
                                                   int(end_date.timestamp()))

                self.sheets_absence.append_absences(start_sheets_absence, end_sheets_absence)
                self._restart_service()

                await interaction.followup.send('Absence has been scheduled successfully.', ephemeral=True)

                # Send to log channel
                activity_message = f'{interaction.user.mention} has scheduled the following absence:\n\n'
                activity_message += f'**Start:** <t:{int(start_date.timestamp())}:F> <t:{int(start_date.timestamp())}:R>\n'
                activity_message += f'**End:** <t:{int(end_date.timestamp())}:F> <t:{int(end_date.timestamp())}:R>\n'
                if duration == 1:
                    activity_message += f'**Duration:** 1 day\n\n'
                else:
                    activity_message += f'**Duration:** {duration:0,.1f} days\n\n'
                activity_message += f'**Bossing parties**\n'
                for member_party in member_parties:
                    activity_message += f'{member_party.boss_name} Party {member_party.party_number}: <#{member_party.party_thread_id}>\n'

                member_activity_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_MEMBER_ACTIVITY)
                await member_activity_channel.send(activity_message)

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
            async def red_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.edit_message(view=None)
                await interaction.followup.send('Absence request cancelled.', ephemeral=True)

        await interaction.followup.send(message, view=Buttons(), ephemeral=True)

    async def status(self, interaction: discord.Interaction):
        user_sheets_absence_start = None
        user_sheets_absence_end = None

        for sheets_absence in self.sheets_absence.absences:
            if sheets_absence.user_id == interaction.user.id:
                if sheets_absence.event_type == SheetsAbsence.Type.start:
                    user_sheets_absence_start = sheets_absence
                elif sheets_absence.event_type == SheetsAbsence.Type.end:
                    user_sheets_absence_end = sheets_absence

        if not user_sheets_absence_start and not user_sheets_absence_end:
            await interaction.followup.send('You have no absence scheduled.', ephemeral=True)
        elif not user_sheets_absence_start:
            await interaction.followup.send(f'You are current away until <t:{user_sheets_absence_end.timestamp}:F>.',
                                            ephemeral=True)
        elif user_sheets_absence_start and user_sheets_absence_end:
            await interaction.followup.send(
                f'You have an absence scheduled from <t:{user_sheets_absence_start.timestamp}:F> to <t:{user_sheets_absence_end.timestamp}:F>.',
                ephemeral=True)
        else:
            await interaction.followup.send(
                f'Error - There is an issue with your scheduled absences. Please contact a <@&{config.GROVE_ROLE_ID_JUNIOR}> to resolve this issue.',
                ephemeral=True)

    async def clear(self, interaction: discord.Interaction):
        if interaction.guild.get_role(config.GROVE_ROLE_ID_AWAY) in interaction.user.roles:
            await interaction.user.remove_roles(
                self.client.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_AWAY))

        delete_sheets_absences = self.sheets_absence.delete_user_absences(interaction.user.id)
        if len(delete_sheets_absences) > 0:
            await interaction.followup.send(f'Scheduled absence has been cleared.', ephemeral=True)
        else:
            await interaction.followup.send(f'No scheduled absences to clear.', ephemeral=True)
