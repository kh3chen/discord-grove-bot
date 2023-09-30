from discord import app_commands
from discord.ext import commands

import config
from away.away import Away

away: Away


class AwayCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name='away', description='Sets your status to Away')
    @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
    @app_commands.describe(start_date='The start date of your absence. Format: MM-DD')
    @app_commands.describe(start_reset_offset='The start time of your absence, relative to MapleStory reset in hours.')
    @app_commands.describe(end_date='The end date of your absence. Format: MM-DD')
    @app_commands.describe(end_reset_offset='The end time of your absence, relative to MapleStory reset in hours.')
    async def away(self, interaction, start_date: str, start_reset_offset: float, end_date: str,
                   end_reset_offset: float):
        await interaction.response.defer(ephemeral=True)
        await away.away(interaction, start_date, start_reset_offset, end_date, end_reset_offset)


async def setup(bot):
    global away
    away = Away(bot)
    await bot.add_cog(AwayCog(bot))
