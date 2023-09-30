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
            start_date = datetime.strptime(start_date_str, '%m-%d').replace(year=now.year, tzinfo=timezone.utc)
        except ValueError:
            await interaction.followup.send(
                f'Error - start_date parameter must be in the format MM-DD, e.g. September 21 as 09-21.',
                ephemeral=True)
            return
        start_date = start_date + timedelta(hours=start_reset_offset)
        if start_date.timestamp() - now.timestamp() < 0:
            start_date = start_date.replace(year=start_date.year + 1)

        days_in_advance = (start_date.timestamp() - now.timestamp()) / Absence.ONE_DAY_IN_SECONDS
        if days_in_advance > 28:
            await interaction.followup.send(
                f'Error - You cannot schedule an absence more than 28 days in advance.',
                ephemeral=True)
            return

        try:
            end_date = datetime.strptime(end_date_str, '%m-%d').replace(year=now.year, tzinfo=timezone.utc)
        except ValueError:
            await interaction.followup.send(
                f'Error - end_date parameter must be in the format MM-DD, e.g. September 21 as 09-21.')
            return
        end_date = end_date + timedelta(hours=end_reset_offset)
        while end_date.timestamp() - start_date.timestamp() < 0:
            end_date = end_date.replace(year=end_date.year + 1)

        duration = (end_date.timestamp() - start_date.timestamp()) / Absence.ONE_DAY_IN_SECONDS

        member_parties = []
        for sheet_party in self.sheets_bossing.parties:
            if (sheet_party.status == Party.PartyStatus.new
                    or sheet_party.status == Party.PartyStatus.open
                    or sheet_party.status == Party.PartyStatus.exclusive):
                for member in self.sheets_bossing.members_dict[sheet_party.role_id]:
                    if member.user_id == str(interaction.user.id):
                        member_parties.append(sheet_party)
                        break

        absence_details = f'**Start:** <t:{int(start_date.timestamp())}:F> <t:{int(start_date.timestamp())}:R>\n'
        absence_details += f'**End:** <t:{int(end_date.timestamp())}:F> <t:{int(end_date.timestamp())}:R>\n'
        if duration == 1:
            absence_details += f'**Duration:** 1 day\n\n'
        else:
            absence_details += f'**Duration:** {duration:0,.1f} days\n\n'
        absence_details += f'**Bossing parties**\n'
        for member_party in member_parties:
            absence_details += f'<@&{member_party.role_id}>: <#{member_party.party_thread_id}>\n'
        confirmation = f'\nBy submitting this absence request, you confirm that:\n1. All bossing parties have been informed of your upcoming absence.\n2. Fills have been found in all parties where your attendance is required to reliably clear.'

        class Buttons(discord.ui.View):
            def __init__(self, *, timeout=180):
                super().__init__(timeout=timeout)

            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
            async def green_button(_self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.edit_message(view=None)
                start_sheets_absence = SheetsAbsence(int(start_date.timestamp()), interaction.user.id,
                                                     SheetsAbsence.Type.start.value)
                end_sheets_absence = SheetsAbsence(int(end_date.timestamp()), interaction.user.id,
                                                   SheetsAbsence.Type.end.value)

                self.sheets_absence.append_absences(start_sheets_absence, end_sheets_absence)
                self._restart_service()

                await interaction.followup.send('Absence has been scheduled successfully.', ephemeral=True)

                # Send to log channel
                log_message = f'{interaction.user.mention} has scheduled the following absence:\n\n'
                log_message += absence_details

                grove_submissions_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_GROVE_SUBMISSIONS)
                await grove_submissions_channel.send(log_message)

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
            async def red_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.edit_message(view=None)
                await interaction.followup.send('Absence request cancelled.', ephemeral=True)

        await interaction.followup.send(absence_details + confirmation, view=Buttons(), ephemeral=True)

    async def clear(self, interaction: discord.Interaction):
        if interaction.guild.get_role(config.GROVE_ROLE_ID_AWAY) in interaction.user.roles:
            await interaction.user.remove_roles(
                self.client.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_AWAY))

        delete_sheets_absences = self.sheets_absence.delete_user_absences(interaction.user.id)
        if len(delete_sheets_absences) > 0:
            await interaction.followup.send(f'Scheduled absence has been cleared.', ephemeral=True)
        else:
            await interaction.followup.send(f'No scheduled absences to clear.', ephemeral=True)
