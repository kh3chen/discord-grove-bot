import discord
from discord import app_commands
from discord.ext import commands

import config
from bossing.bossing import Bossing

bossing: Bossing


class ModBossingGroup(app_commands.Group, name='mod-bossing', description='Mod bossing commands'):

    def __init__(self):
        super().__init__()
        self.add_command(ModBossingGroup.ModBossingMemberGroup())
        self.add_command(ModBossingGroup.ModBossingPartyGroup())

    @app_commands.command(name='listremake', description='Remake the bossing party list')
    @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
    async def listremake(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await bossing.listremake(interaction)

    @app_commands.command(name='sync',
                          description="Sync Grove Bot to any manually changed data in the Boss Parties spreadsheet")
    @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await bossing.sync(interaction)

    class ModBossingMemberGroup(app_commands.Group, name='member',
                                description='Mod bossing member commands'):

        @app_commands.command(name='add', description='Add a bossing party role to a member')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        async def add(self, interaction: discord.Interaction, user: discord.Member, boss_party_role: discord.Role,
                      job: str):
            await interaction.response.defer(ephemeral=True)
            await bossing.add(interaction, user, boss_party_role, job)

        @app_commands.command(name='remove', description='Remove a bossing party role from a member')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        async def remove(self, interaction: discord.Interaction, user: discord.Member, boss_party_role: discord.Role,
                         job: str = ''):
            await interaction.response.defer(ephemeral=True)
            await bossing.remove(interaction, user, boss_party_role, job)

    class ModBossingPartyGroup(app_commands.Group, name='party', description='Mod bossing party commands'):

        @app_commands.command(name='settime', description='Set the bossing party time')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        @app_commands.describe(weekday='day of week: [ mon | tue | wed | thu | fri | sat | sun ]')
        @app_commands.describe(hour='hour relative to reset: [0-23]')
        @app_commands.describe(minute='minute of the hour: [0-59]')
        async def settime(self, interaction: discord.Interaction, boss_party_role: discord.Role, weekday: str,
                          hour: int,
                          minute: int = 0):
            await interaction.response.defer(ephemeral=True)
            await bossing.mod_settime(interaction, boss_party_role, weekday, hour, minute)

        @app_commands.command(name='cleartime', description='Clear the bossing party time')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        async def cleartime(self, interaction: discord.Interaction, boss_party_role: discord.Role):
            await interaction.response.defer(ephemeral=True)
            await bossing.mod_cleartime(interaction, boss_party_role)

        @app_commands.command(name='new', description='Create a new bossing party')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        async def new(self, interaction: discord.Interaction, boss_name: str):
            await interaction.response.defer(ephemeral=True)
            await bossing.new(interaction, boss_name)

        @app_commands.command(name='open', description='Make a new or exclusive party open')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        async def open(self, interaction: discord.Interaction, boss_party_role: discord.Role):
            await interaction.response.defer(ephemeral=True)
            await bossing.open(interaction, boss_party_role)

        @app_commands.command(name='exclusive', description='Make a new or open party exclusive')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        async def exclusive(self, interaction: discord.Interaction, boss_party_role: discord.Role):
            await interaction.response.defer(ephemeral=True)
            await bossing.exclusive(interaction, boss_party_role)

        @app_commands.command(name='retire', description='Retire a party, removing all of its party members')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        async def retire(self, interaction: discord.Interaction, boss_party_role: discord.Role):
            await interaction.response.defer()
            await bossing.retire(interaction, boss_party_role)


class UserBossingPartyGroup(app_commands.Group, name='party', description='Bossing party commands'):

    @app_commands.command(name='settime', description='Set the bossing party time')
    @app_commands.describe(weekday='day of week: [ mon | tue | wed | thu | fri | sat | sun ]')
    @app_commands.describe(hour='hour relative to reset: [0-23]')
    @app_commands.describe(minute='minute of the hour: [0-59]')
    async def settime(self, interaction: discord.Interaction, weekday: str, hour: int,
                      minute: int = 0):
        await interaction.response.defer(ephemeral=True)
        await bossing.user_settime(interaction, weekday, hour, minute)

    @app_commands.command(name='cleartime', description='Clear the bossing party time')
    async def cleartime(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await bossing.user_cleartime(interaction)


class BossingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    mod_bossing = ModBossingGroup()
    bossing = app_commands.Group(name='bossing', description='Bossing commands')
    bossing.add_command(UserBossingPartyGroup())

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'BossCog on_ready')
        print('------')
        bossing.on_ready()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await bossing.on_member_remove(member)

    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        await interaction.response.defer(ephemeral=True)
        if isinstance(error, app_commands.errors.MissingRole):
            error_message = str(error).replace(str(config.GROVE_ROLE_ID_JUNIOR), f'<@&{config.GROVE_ROLE_ID_JUNIOR}>')
            await interaction.followup.send(error_message)
        else:
            await interaction.followup.send(error)


async def setup(bot):
    global bossing
    bossing = Bossing(bot)
    await bot.add_cog(BossingCog(bot))
