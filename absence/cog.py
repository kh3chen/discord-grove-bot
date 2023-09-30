from discord import app_commands
from discord.ext import commands

from absence.absence import Absence

absence: Absence


class AbsenceGroup(app_commands.Group, name='absence', description='Commands to manage Away role and requests'):

    @app_commands.command(name='schedule', description='Schedule an absence')
    @app_commands.describe(start_date='The start date of your absence. Format: MM-DD')
    @app_commands.describe(start_reset_offset='The start time of your absence, relative to MapleStory reset in hours.')
    @app_commands.describe(end_date='The end date of your absence. Format: MM-DD')
    @app_commands.describe(end_reset_offset='The end time of your absence, relative to MapleStory reset in hours.')
    async def schedule(self, interaction, start_date: str, start_reset_offset: float, end_date: str,
                       end_reset_offset: float):
        await interaction.response.defer(ephemeral=True)
        await absence.schedule(interaction, start_date, start_reset_offset, end_date, end_reset_offset)

    @app_commands.command(name='clear', description='Clear any existing and future scheduled absences')
    async def clear(self, interaction):
        await interaction.response.defer(ephemeral=True)
        await absence.clear(interaction)


class AbsenceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'AbsenceCog on_ready')
        print('------')
        absence.on_ready()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await absence.on_member_remove(member)


    absence_group = AbsenceGroup()


async def setup(bot):
    global absence
    absence = Absence(bot)
    await bot.add_cog(AbsenceCog(bot))
