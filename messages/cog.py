import discord
from discord import app_commands
from discord.app_commands.commands import ContextMenuCallback
from discord.ext import commands

import config


class ModMessagesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.__add_context_menu('Move to #maple-gains', self.message_gains)

    def __add_context_menu(self, name: str, callback: ContextMenuCallback):
        context_menu = app_commands.ContextMenu(
            name=name,
            callback=callback
        )
        self.bot.tree.add_command(context_menu)

    async def message_gains(self, interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)
        if not message.is_forwardable():
            await interaction.followup.send(
                content=f'Error - This message cannot be forwarded.')
            return

        if message.channel.id != config.GROVE_CHANNEL_ID_MAPLE_CHAT:
            await interaction.followup.send(
                content=f'Error - Can only be used for messages sent in <#{config.GROVE_CHANNEL_ID_MAPLE_CHAT}>.')
            return

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
                maple_gains_channel = interaction.guild.get_channel(config.GROVE_CHANNEL_ID_MAPLE_GAINS)
                await maple_gains_channel.send(message.author.mention)
                forward_message = await message.forward(maple_gains_channel)
                await message.reply(f'This message has been moved: {forward_message.jump_url}')
                await message.delete()

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
            async def red_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                self.interacted = True
                await button_interaction.response.edit_message(view=None)
                await interaction.followup.send('Move to #maple-gains cancelled.', ephemeral=True)

        buttonsView = Buttons()
        buttonsView.message = await interaction.followup.send(
            f'Are you sure you want to move the message to<#{config.GROVE_CHANNEL_ID_MAPLE_GAINS}>? The original message will be deleted.',
            view=buttonsView, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModMessagesCog(bot))
