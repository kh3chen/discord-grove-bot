import discord
from discord import app_commands
from discord.ext import commands

import announcement
import config
import release
from bossparty import BossParty

MY_GUILD = discord.Object(id=config.GROVE_GUILD_ID)
bossparty: BossParty


class GroveBot(commands.Bot):

    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def setup_hook(self):
        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
grovebot = GroveBot(command_prefix='>', intents=intents)


@grovebot.event
async def on_ready():
    print(f'Logged in as {grovebot.user} (ID: {grovebot.user.id})')
    print('------')
    global bossparty
    bossparty = BossParty(grovebot)


@grovebot.command()
async def version(ctx):
    await ctx.send(release.version_name)


@grovebot.hybrid_command(name='announcement', brief='Sends the weekly Grove announcement')
@commands.has_role('Junior')
@app_commands.describe(emoji='The seasonal Grove tree emoji')
@app_commands.describe(custom_msg_id='The message ID you want to copy for the custom announcement')
async def _announcement(ctx, emoji: str, custom_msg_id: str = None):
    await announcement.send_announcement(grovebot, ctx, emoji, custom_msg_id)


@grovebot.event
async def on_member_remove(member):
    await grovebot.bossparty.on_member_remove(member)


@app_commands.guild_only()
class BossGroup(app_commands.Group):
    def __init__(self, client: discord.Client):
        super().__init__(name="boss", description="Boss commands")

    @app_commands.command(name='sync',
                          description="Sync Grove Bot to any manually changed data in the Boss Parties spreadsheet")
    @app_commands.checks.has_role("Junior")
    async def bossparty_sync(self, interaction):
        await interaction.response.defer(ephemeral=True)
        await bossparty.sync(interaction)

    @app_commands.command(name='add', description='Add a boss party role to a member')
    @app_commands.checks.has_role("Junior")
    async def bossparty_add(self, interaction, user: discord.Member, boss_party_role: discord.Role, job: str):
        await interaction.response.defer(ephemeral=True)
        await bossparty.add(interaction, user, boss_party_role, job)

    @app_commands.command(name='remove', description='Remove a boss party role from a member')
    @app_commands.checks.has_role("Junior")
    async def bossparty_remove(self, interaction, user: discord.Member, boss_party_role: discord.Role, job: str = ''):
        await interaction.response.defer(ephemeral=True)
        await bossparty.remove(interaction, user, boss_party_role, job)

    @app_commands.command(name='create', description='Create a new boss party')
    @app_commands.checks.has_role("Junior")
    async def bossparty_create(self, interaction, boss_name: str):
        await interaction.response.defer(ephemeral=True)
        await bossparty.create(interaction, boss_name)

    @app_commands.command(name='settime', description='Set the boss party time')
    @app_commands.checks.has_role("Junior")
    @app_commands.describe(weekday='day of week: [ mon | tue | wed | thu | fri | sat | sun ]')
    @app_commands.describe(hour='hour relative to reset: [0-23]')
    @app_commands.describe(minute='minute of the hour: [0-59]')
    async def bossparty_settime(self, interaction, boss_party_role: discord.Role, weekday: str, hour: int,
                                minute: int = 0):
        await interaction.response.defer(ephemeral=True)
        await bossparty.settime(interaction, boss_party_role, weekday, hour, minute)

    @app_commands.command(name='cleartime', description='Clear the boss party time')
    @app_commands.checks.has_role("Junior")
    async def bossparty_cleartime(self, interaction, boss_party_role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        await bossparty.cleartime(interaction, boss_party_role)

    @app_commands.command(name='exclusive', description='Make a party exclusive')
    @app_commands.checks.has_role("Junior")
    async def bossparty_exclusive(self, interaction, boss_party_role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        await bossparty.exclusive(interaction, boss_party_role)

    @app_commands.command(name='open', description='Make a party open')
    @app_commands.checks.has_role("Junior")
    async def bossparty_open(self, interaction, boss_party_role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        await bossparty.open(interaction, boss_party_role)

    @app_commands.command(name='retire', description='Retire a party, removing all of its party members')
    @app_commands.checks.has_role("Junior")
    async def bossparty_retire(self, interaction, boss_party_role: discord.Role):
        await bossparty.retire(interaction, boss_party_role)

    @app_commands.command(name='listremake', description='Remake the boss party list')
    @app_commands.checks.has_role("Junior")
    async def bossparty_listremake(self, interaction):
        await interaction.response.defer()
        await bossparty.listremake(interaction)


grovebot.tree.add_command(BossGroup(grovebot))
grovebot.run(config.BOT_TOKEN)
