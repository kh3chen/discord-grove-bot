from discord import app_commands
from discord.ext import commands

from birthday.birthday import Birthday

birthday: Birthday


class BirthdayGroup(app_commands.Group, name='birthday', description='Commands to manage Birthday'):

    @app_commands.command(name='set', description='Set your birthday')
    @app_commands.describe(day='Your birthday! Format: MM-DD')
    @app_commands.describe(reset_offset='When to announce your birthday, relative to MapleStory reset in hours.')
    async def set(self, interaction, day: str, reset_offset: float):
        await interaction.response.defer(ephemeral=True)
        await birthday.set(interaction, day, reset_offset)

    @app_commands.command(name='status', description='Check your birthday settings')
    async def status(self, interaction):
        await interaction.response.defer(ephemeral=True)
        await birthday.status(interaction)

    @app_commands.command(name='clear', description='Clear your set birthday')
    async def clear(self, interaction):
        await interaction.response.defer(ephemeral=True)
        await birthday.clear(interaction)

    @app_commands.command(name='upcoming', description='Get a list of upcoming birthdays')
    async def upcoming(self, interaction):
        await interaction.response.defer()
        await birthday.upcoming(interaction)


class BirthdayCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'BirthdayCog on_ready')
        print('------')
        birthday.on_ready()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await birthday.on_member_remove(member)

    absence_group = BirthdayGroup()


async def setup(bot):
    global birthday
    birthday = Birthday(bot)
    await bot.add_cog(BirthdayCog(bot))
