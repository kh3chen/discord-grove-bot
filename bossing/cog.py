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

        @app_commands.command(name='new', description='Create a new bossing party')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        async def new(self, interaction: discord.Interaction, boss_name: str, difficulty: str = ""):
            await interaction.response.defer(ephemeral=True)
            await bossing.new(interaction, boss_name, difficulty)

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
            await interaction.response.defer(ephemeral=True)
            await bossing.retire(interaction, boss_party_role)

        @app_commands.command(name='difficulty',
                              description='Set a boss party difficulty for bosses that support it')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        async def difficulty(self, interaction: discord.Interaction, boss_party_role: discord.Role, difficulty: str):
            await interaction.response.defer(ephemeral=True)
            await bossing.difficulty(interaction, boss_party_role, difficulty)

        @app_commands.command(name='settime-recurring', description='Set the recurring bossing party time')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        @app_commands.describe(weekday='day of week: [ mon | tue | wed | thu | fri | sat | sun ]')
        @app_commands.describe(hour='hour relative to reset: [0-23]')
        @app_commands.describe(minute='minute of the hour: [0-59]')
        async def set_recurring(self, interaction: discord.Interaction, boss_party_role: discord.Role, weekday: str,
                                hour: int,
                                minute: int = 0):
            await interaction.response.defer(ephemeral=True)
            await bossing.mod_set_recurring_time(interaction, boss_party_role, weekday, hour, minute)

        @app_commands.command(name='cleartime-recurring', description='Clear the recurring bossing party time')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        async def clear_recurring(self, interaction: discord.Interaction, boss_party_role: discord.Role):
            await interaction.response.defer(ephemeral=True)
            await bossing.mod_clear_recurring_time(interaction, boss_party_role)

        @app_commands.command(name='settime-one', description='Set the one-time bossing party time')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        @app_commands.describe(date='The date of the run in UTC. Format: YYYY-MM-DD')
        @app_commands.describe(hour='hour relative to reset: [0-23]')
        @app_commands.describe(minute='minute of the hour: [0-59]')
        async def set_one_time(self, interaction: discord.Interaction, boss_party_role: discord.Role, date: str,
                               hour: int, minute: int):
            await interaction.response.defer(ephemeral=True)
            await bossing.mod_set_one_time(interaction, boss_party_role, date, hour, minute)

        @app_commands.command(name='cleartime-one', description='Clear the one-time bossing party time')
        @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
        async def clear_one_time(self, interaction: discord.Interaction, boss_party_role: discord.Role):
            await interaction.response.defer(ephemeral=True)
            await bossing.mod_clear_one_time(interaction, boss_party_role)


class UserBossingGroup(app_commands.Group, name='bossing', description='Bossing commands'):

    def __init__(self):
        super().__init__()
        self.add_command(UserBossingGroup.UserBossingPartyGroup())

    class UserBossingPartyGroup(app_commands.Group, name='party', description='Bossing party commands'):

        @app_commands.command(name='settime-recurring', description='Set the recurring bossing party time')
        @app_commands.describe(weekday='day of week: [ mon | tue | wed | thu | fri | sat | sun ]')
        @app_commands.describe(hour='hour relative to reset: [0-23]')
        @app_commands.describe(minute='minute of the hour: [0-59]')
        async def set_recurring(self, interaction: discord.Interaction, weekday: str, hour: int,
                                minute: int = 0):
            await interaction.response.defer(ephemeral=True)
            await bossing.user_set_recurring_time(interaction, weekday, hour, minute)

        @app_commands.command(name='cleartime-recurring', description='Clear the recurring bossing party time')
        async def clear_recurring(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            await bossing.user_clear_recurring_time(interaction)

        @app_commands.command(name='settime-one', description='Set the one-time bossing party time')
        @app_commands.describe(date='The date of the run in UTC. Format: YYYY-MM-DD')
        @app_commands.describe(hour='hour relative to reset: [0-23]')
        @app_commands.describe(minute='minute of the hour: [0-59]')
        async def set_one_time_2(self, interaction: discord.Interaction, date: str, hour: int, minute: int):
            await interaction.response.defer(ephemeral=True)
            await bossing.user_set_one_time(interaction, date, hour, minute)

        @app_commands.command(name='cleartime-one', description='Clear the one-time bossing party time')
        async def clear_one_time(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            await bossing.user_clear_one_time(interaction)

        @app_commands.command(name='nexttime', description='Get the next party run time')
        async def next_time(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            await bossing.user_next_time(interaction)


class BossingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    mod_bossing = ModBossingGroup()
    user_bossing = UserBossingGroup()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'BossCog on_ready')
        print('------')
        bossing.on_ready()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await bossing.remove_member_from_bossing_parties(member, True)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        try:
            new_roles = [role for role in after.roles if role not in before.roles]
            retiree_role = next(role for role in new_roles if
                                role.id == config.GROVE_ROLE_ID_FRIEND)
            # Retiree role was added
            print(f'{after.mention} is retiree, removing from bossing parties')
            await bossing.remove_member_from_bossing_parties(after, False)
        except StopIteration:
            return

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
