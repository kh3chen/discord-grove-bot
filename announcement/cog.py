from discord import app_commands
from discord.ext import commands

import config
from announcement import announcement


class AnnouncementCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name='announcement', description='Sends the weekly Grove announcement')
    @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
    @app_commands.describe(emoji='The seasonal Grove tree emoji')
    @app_commands.describe(custom_msg_id='The message ID you want to copy for the custom announcement')
    async def _announcement(self, interaction, emoji: str, custom_msg_id: str = None):
        await interaction.response.defer()
        await announcement.send_announcement(self.bot, interaction, emoji, custom_msg_id)


async def setup(bot):
    await bot.add_cog(AnnouncementCog(bot))
