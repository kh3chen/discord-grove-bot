import discord
from discord import app_commands

from bossing.bossing import Bossing


@app_commands.guild_only()
class BossingGroup(app_commands.Group):
    def __init__(self, bossing: Bossing):
        super().__init__(name="bossing", description="Boss commands")
        self.bossing = bossing

    @app_commands.command(name='sync',
                          description="Sync Grove Bot to any manually changed data in the Boss Parties spreadsheet")
    @app_commands.checks.has_role("Junior")
    async def sync(self, interaction):
        await interaction.response.defer(ephemeral=True)
        await self.bossing.sync(interaction)

    @app_commands.command(name='add', description='Add a bossing party role to a member')
    @app_commands.checks.has_role("Junior")
    async def add(self, interaction, user: discord.Member, boss_party_role: discord.Role, job: str):
        await interaction.response.defer(ephemeral=True)
        await self.bossing.add(interaction, user, boss_party_role, job)

    @app_commands.command(name='remove', description='Remove a bossing party role from a member')
    @app_commands.checks.has_role("Junior")
    async def remove(self, interaction, user: discord.Member, boss_party_role: discord.Role, job: str = ''):
        await interaction.response.defer(ephemeral=True)
        await self.bossing.remove(interaction, user, boss_party_role, job)

    @app_commands.command(name='create', description='Create a new bossing party')
    @app_commands.checks.has_role("Junior")
    async def create(self, interaction, boss_name: str):
        await interaction.response.defer(ephemeral=True)
        await self.bossing.create(interaction, boss_name)

    @app_commands.command(name='settime', description='Set the bossing party time')
    @app_commands.checks.has_role("Junior")
    @app_commands.describe(weekday='day of week: [ mon | tue | wed | thu | fri | sat | sun ]')
    @app_commands.describe(hour='hour relative to reset: [0-23]')
    @app_commands.describe(minute='minute of the hour: [0-59]')
    async def settime(self, interaction, boss_party_role: discord.Role, weekday: str, hour: int,
                                minute: int = 0):
        await interaction.response.defer(ephemeral=True)
        await self.bossing.settime(interaction, boss_party_role, weekday, hour, minute)

    @app_commands.command(name='cleartime', description='Clear the bossing party time')
    @app_commands.checks.has_role("Junior")
    async def cleartime(self, interaction, boss_party_role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        await self.bossing.cleartime(interaction, boss_party_role)

    @app_commands.command(name='exclusive', description='Make a party exclusive')
    @app_commands.checks.has_role("Junior")
    async def exclusive(self, interaction, boss_party_role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        await self.bossing.exclusive(interaction, boss_party_role)

    @app_commands.command(name='open', description='Make a party open')
    @app_commands.checks.has_role("Junior")
    async def open(self, interaction, boss_party_role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        await self.bossing.open(interaction, boss_party_role)

    @app_commands.command(name='retire', description='Retire a party, removing all of its party members')
    @app_commands.checks.has_role("Junior")
    async def retire(self, interaction, boss_party_role: discord.Role):
        await self.bossing.retire(interaction, boss_party_role)

    @app_commands.command(name='listremake', description='Remake the bossing party list')
    @app_commands.checks.has_role("Junior")
    async def listremake(self, interaction):
        await interaction.response.defer()
        await self.bossing.listremake(interaction)
