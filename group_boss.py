import discord
from discord import app_commands

from bossparty import BossParty


@app_commands.guild_only()
class BossGroup(app_commands.Group):
    def __init__(self, bossparty):
        super().__init__(name="bossparty", description="Boss commands")
        self.bossparty = bossparty

    @app_commands.command(name='sync',
                          description="Sync Grove Bot to any manually changed data in the Boss Parties spreadsheet")
    @app_commands.checks.has_role("Junior")
    async def bossparty_sync(self, interaction):
        await interaction.response.defer(ephemeral=True)
        await self.bossparty.sync(interaction)

    @app_commands.command(name='add', description='Add a boss party role to a member')
    @app_commands.checks.has_role("Junior")
    async def bossparty_add(self, interaction, user: discord.Member, boss_party_role: discord.Role, job: str):
        await interaction.response.defer(ephemeral=True)
        await self.bossparty.add(interaction, user, boss_party_role, job)

    @app_commands.command(name='remove', description='Remove a boss party role from a member')
    @app_commands.checks.has_role("Junior")
    async def bossparty_remove(self, interaction, user: discord.Member, boss_party_role: discord.Role, job: str = ''):
        await interaction.response.defer(ephemeral=True)
        await self.bossparty.remove(interaction, user, boss_party_role, job)

    @app_commands.command(name='create', description='Create a new boss party')
    @app_commands.checks.has_role("Junior")
    async def bossparty_create(self, interaction, boss_name: str):
        await interaction.response.defer(ephemeral=True)
        await self.bossparty.create(interaction, boss_name)

    @app_commands.command(name='settime', description='Set the boss party time')
    @app_commands.checks.has_role("Junior")
    @app_commands.describe(weekday='day of week: [ mon | tue | wed | thu | fri | sat | sun ]')
    @app_commands.describe(hour='hour relative to reset: [0-23]')
    @app_commands.describe(minute='minute of the hour: [0-59]')
    async def bossparty_settime(self, interaction, boss_party_role: discord.Role, weekday: str, hour: int,
                                minute: int = 0):
        await interaction.response.defer(ephemeral=True)
        await self.bossparty.settime(interaction, boss_party_role, weekday, hour, minute)

    @app_commands.command(name='cleartime', description='Clear the boss party time')
    @app_commands.checks.has_role("Junior")
    async def bossparty_cleartime(self, interaction, boss_party_role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        await self.bossparty.cleartime(interaction, boss_party_role)

    @app_commands.command(name='exclusive', description='Make a party exclusive')
    @app_commands.checks.has_role("Junior")
    async def bossparty_exclusive(self, interaction, boss_party_role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        await self.bossparty.exclusive(interaction, boss_party_role)

    @app_commands.command(name='open', description='Make a party open')
    @app_commands.checks.has_role("Junior")
    async def bossparty_open(self, interaction, boss_party_role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        await self.bossparty.open(interaction, boss_party_role)

    @app_commands.command(name='retire', description='Retire a party, removing all of its party members')
    @app_commands.checks.has_role("Junior")
    async def bossparty_retire(self, interaction, boss_party_role: discord.Role):
        await self.bossparty.retire(interaction, boss_party_role)

    @app_commands.command(name='listremake', description='Remake the boss party list')
    @app_commands.checks.has_role("Junior")
    async def bossparty_listremake(self, interaction):
        await interaction.response.defer()
        await self.bossparty.listremake(interaction)