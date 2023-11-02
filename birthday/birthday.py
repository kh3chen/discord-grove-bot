from datetime import datetime

import discord

import config
from birthday.service import BirthdayService
from birthday.sheets import Birthday as SheetsBirthday
from birthday.sheets import BirthdaySheets


class Birthday:

    def __init__(self, client):
        self.client = client
        self.sheets_birthday = BirthdaySheets()

        async def on_start_birthday(sheets_birthday: SheetsBirthday):
            member: discord.Member = self.client.get_guild(config.GROVE_GUILD_ID).get_member(sheets_birthday.user_id)
            if member:
                # Check if the Birthday role is already set
                try:
                    next(role for role in member.roles if role.id == config.GROVE_ROLE_ID_BIRTHDAY)
                    # Member already has Birthday role
                    return
                except StopIteration:
                    pass

                # Set the Birthday role
                await member.add_roles(
                    self.client.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_BIRTHDAY))

                # Send Happy Birthday message
                send_channel = self.client.get_channel(config.GROVE_CHANNEL_ID_GENERAL)
                birthday_message_body = f'Happy Birthday, {member.mention}!'
                birthday_message = await send_channel.send(birthday_message_body)
                await birthday_message.add_reaction('🎂')

        async def on_end_birthday(sheets_birthday: SheetsBirthday):
            # Clear the Birthday role
            member = self.client.get_guild(config.GROVE_GUILD_ID).get_member(sheets_birthday.user_id)
            if member:
                await member.remove_roles(
                    self.client.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_BIRTHDAY))

        self.birthday_service = BirthdayService(on_start_birthday, on_end_birthday)

    def _restart_service(self):
        self.birthday_service.restart_service(self.sheets_birthday.birthdays)

    def on_ready(self):
        self._restart_service()

    def on_member_remove(self, member: discord.Member):
        deleted_sheets_birthday = self.sheets_birthday.delete_user_birthday(member.id)
        if deleted_sheets_birthday:
            self._restart_service()

    async def set(self, interaction: discord.Interaction, birthday_str: str, reset_offset: float):
        now = datetime.now()

        try:
            next_birthday = SheetsBirthday.get_next_birthday(birthday_str, reset_offset)
        except ValueError:
            await interaction.followup.send(
                f'Error - birthday_str parameter must be in the format MM-DD, e.g. November 3 as 11-03.',
                ephemeral=True)
            return

        existing_sheets_birthday = None
        existing_birthday = None
        try:
            existing_sheets_birthday = next(sheets_birthday for sheets_birthday in self.sheets_birthday.birthdays if
                                            sheets_birthday.user_id == interaction.user.id)
            existing_birthday = SheetsBirthday.get_next_birthday(existing_sheets_birthday.birthday_str,
                                                                 existing_sheets_birthday.reset_offset)
        except StopIteration:
            pass

        if existing_birthday:
            message = f'Do you want to update your birthday?\n\n'
            message += f'Your existing birthday: <t:{int(existing_birthday.timestamp())}:F>\n'
            message += f'Your updated birthday: <t:{int(next_birthday.timestamp())}:F>'
        else:
            message = f'Do you want to set your birthday?\n\n'
            message += f'Your birthday: <t:{int(next_birthday.timestamp())}:F>'

        class Buttons(discord.ui.View):
            def __init__(self, *, timeout=180):
                super().__init__(timeout=timeout)

            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
            async def green_button(_self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.edit_message(view=None)
                if existing_sheets_birthday:
                    existing_sheets_birthday.birthday_str = birthday_str
                    existing_sheets_birthday.reset_offset = reset_offset
                    self.sheets_birthday.update_birthdays(self.sheets_birthday.birthdays)
                else:
                    self.sheets_birthday.append_birthday(
                        SheetsBirthday(interaction.user.id, birthday_str, reset_offset))

                self._restart_service()

                confirm_message = 'Your birthday has been set!\n\n'

                if next_birthday.timestamp() - now.timestamp() < 0:
                    confirm_message += f'It\'s your birthday today! It started on <t:{int(next_birthday.timestamp())}:F>.\n\nHappy Birthday! :birthday:'
                else:
                    confirm_message += f'Your next birthday is on <t:{int(next_birthday.timestamp())}:F>.'

                await interaction.followup.send(confirm_message, ephemeral=True)

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
            async def red_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.edit_message(view=None)
                await interaction.followup.send('Setting your birthday has been cancelled.', ephemeral=True)

        await interaction.followup.send(message, view=Buttons(), ephemeral=True)

    async def status(self, interaction: discord.Interaction):
        user_sheets_birthday = None

        for sheets_birthday in self.sheets_birthday.birthdays:
            if sheets_birthday.user_id == interaction.user.id:
                user_sheets_birthday = sheets_birthday
                break

        if user_sheets_birthday:
            now = datetime.now()
            user_birthday = SheetsBirthday.get_next_birthday(user_sheets_birthday.birthday_str,
                                                             user_sheets_birthday.reset_offset)
            if user_birthday.timestamp() - now.timestamp() < 0:
                await interaction.followup.send(
                    f'It\'s your birthday today! It started on <t:{int(user_birthday.timestamp())}:F>.\n\nHappy Birthday! :birthday:')
            else:
                await interaction.followup.send(f'Your next birthday is on <t:{int(user_birthday.timestamp())}:F>.')
        else:
            await interaction.followup.send('You do not have a birthday set.', ephemeral=True)

    async def clear(self, interaction: discord.Interaction):
        if interaction.guild.get_role(config.GROVE_ROLE_ID_BIRTHDAY) in interaction.user.roles:
            await interaction.user.remove_roles(
                self.client.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_BIRTHDAY))

        delete_sheets_birthday = self.sheets_birthday.delete_user_birthday(interaction.user.id)

        if delete_sheets_birthday:
            deleted_next_birthday = SheetsBirthday.get_next_birthday(delete_sheets_birthday.birthday_str,
                                                                     delete_sheets_birthday.reset_offset)
            await interaction.followup.send(
                f'Your set birthday on <t:{int(deleted_next_birthday.timestamp())}:F> has been cleared.',
                ephemeral=True)
        else:
            await interaction.followup.send(f'No set birthday to clear.', ephemeral=True)

    async def upcoming(self, interaction: discord.Interaction):
        await interaction.followup.send(f'Sorry, this functionality is not available yet.', ephemeral=True)
