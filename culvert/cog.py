from discord import app_commands
from discord.ext import commands

from culvert import culvert


class CulvertCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name='culvert', description='See your Grove Culvert scores')
    @app_commands.describe(ign='Character name')
    async def culvert(self, interaction, ign: str):
        await interaction.response.defer()
        await culvert.culvert(interaction, ign)


async def setup(bot):
    await bot.add_cog(CulvertCog(bot))
