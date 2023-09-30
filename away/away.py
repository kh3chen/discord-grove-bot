from datetime import datetime, timezone, timedelta

import discord

import config
from away.service import AwayService
from away.sheets import Away as SheetsAway
from away.sheets import AwaySheets
from bossing.sheets import BossingSheets, Party


class Away:
    ONE_DAY_IN_SECONDS = 86400

    def __init__(self, client):
        self.client = client
        self.sheets_bossing = BossingSheets()
        self.sheets_away = AwaySheets()

        async def on_set_away(sheets_away: SheetsAway):
            # Set the Away role
            member = self.client.get_guild(config.GROVE_GUILD_ID).get_member(sheets_away.user_id)
            await member.add_roles(self.client.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_AWAY))
            # Delete the away event
            self.sheets_away.delete_away(sheets_away)

        async def on_clear_away(sheets_away: SheetsAway):
            # Clear the Away role
            member = self.client.get_guild(config.GROVE_GUILD_ID).get_member(sheets_away.user_id)
            await member.remove_roles(self.client.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_AWAY))
            # Delete the away event
            self.sheets_away.delete_away(sheets_away)

        self.away_service = AwayService(on_set_away, on_clear_away)

    async def away(self, interaction: discord.Interaction, start_date_str: str, start_reset_offset: float,
                   end_date_str: str,
                   end_reset_offset: float):
        # TODO: Validate with existing away. Options are only allow one, or prevent overlap
        now = datetime.now()

        try:
            start_date = datetime.strptime(start_date_str, '%m-%d').replace(year=now.year, tzinfo=timezone.utc)
        except ValueError:
            await interaction.followup.send(
                f'Error - start_date parameter must be in the format MM-DD, e.g. September 21 as 09-21.')
            return
        start_date = start_date + timedelta(hours=start_reset_offset)
        if start_date.timestamp() - now.timestamp() < 0:
            start_date = start_date.replace(year=start_date.year + 1)

        days_in_advance = (start_date.timestamp() - now.timestamp()) / Away.ONE_DAY_IN_SECONDS
        # TODO: add validation so days in advance is not more than... 3 months? 1 month? 28 days?

        try:
            end_date = datetime.strptime(end_date_str, '%m-%d').replace(year=now.year, tzinfo=timezone.utc)
        except ValueError:
            await interaction.followup.send(
                f'Error - end_date parameter must be in the format MM-DD, e.g. September 21 as 09-21.')
            return
        end_date = end_date + timedelta(hours=end_reset_offset)
        while end_date.timestamp() - start_date.timestamp() < 0:
            end_date = end_date.replace(year=end_date.year + 1)

        days_away = (end_date.timestamp() - start_date.timestamp()) / Away.ONE_DAY_IN_SECONDS
        # TODO: add validation so days away is not more than... 21?

        member_parties = []
        for sheet_party in self.sheets_bossing.parties:
            if (sheet_party.status == Party.PartyStatus.new.name
                    or sheet_party.status == Party.PartyStatus.new.open.name
                    or sheet_party.status == Party.PartyStatus.new.exclusive.name):
                for member in self.sheets_bossing.members_dict[sheet_party.role_id]:
                    if member.user_id == str(interaction.user.id):
                        member_parties.append(sheet_party)
                        break

        message = f'Away from <t:{int(start_date.timestamp())}:F> to <t:{int(end_date.timestamp())}:F>\n'
        message += f'Starts in {days_in_advance} days. Away for {days_away} days.\n\n'
        message += f'Bossing parties:\n'
        for member_party in member_parties:
            message += f'{member_party.boss_name} Party {member_party.party_number} <#{member_party.party_thread_id}>\n'

        class Buttons(discord.ui.View):
            def __init__(self, *, timeout=180):
                super().__init__(timeout=timeout)

            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
            async def green_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.edit_message(view=None)
                # TODO: sheets stuff
                await interaction.followup.send('Away has been scheduled.', ephemeral=True)

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
            async def red_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.edit_message(view=None)
                await interaction.followup.send('Away cancelled.', ephemeral=True)

        await interaction.followup.send(message, view=Buttons(), ephemeral=True)
