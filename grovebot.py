import discord
from discord import app_commands
from discord.ext import commands

import announcement
import config
import release
from bossparty import BossParty


class GroveBot(commands.Bot):
    bossparty: BossParty

    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix='>', intents=intents)


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = GroveBot(command_prefix='>', intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    bot.bossparty = BossParty(bot)
    await bot.tree.sync()
    print('Command tree synced.')


@bot.command()
async def version(ctx):
    await ctx.send(release.version_name)


@bot.hybrid_command(name='announcement', brief='Sends the weekly Grove announcement')
@commands.has_role('Junior')
@app_commands.describe(emoji='The seasonal Grove tree emoji')
@app_commands.describe(custom_msg_id='The message ID you want to copy for the custom announcement')
async def _announcement(ctx, emoji: str, custom_msg_id: str = None):
    await announcement.send_announcement(bot, ctx, emoji, custom_msg_id)


@bot.hybrid_group(name='bossparty')
async def _bossparty(ctx):
    pass


@_bossparty.command(name='sync', brief="Sync Grove Bot to any manually changed data in the Boss Parties spreadsheet")
@commands.has_role('Junior')
async def bossparty_sync(ctx):
    await ctx.defer(ephemeral=True)
    await bot.bossparty.sync(ctx)


@_bossparty.command(name='add', brief='Add a boss party role to a member')
@commands.has_role('Junior')
async def bossparty_add(ctx, user: discord.Member, boss_party_role: discord.Role, job: str):
    await ctx.defer(ephemeral=True)
    await bot.bossparty.add(ctx, user, boss_party_role, job)


@_bossparty.command(name='remove', brief='Remove a boss party role from a member')
@commands.has_role('Junior')
async def bossparty_remove(ctx, user: discord.Member, boss_party_role: discord.Role, job=''):
    await ctx.defer(ephemeral=True)
    await bot.bossparty.remove(ctx, user, boss_party_role, job)


@_bossparty.command(name='create', brief='Create a new boss party')
@commands.has_role('Junior')
async def bossparty_create(ctx, boss_name):
    await ctx.defer(ephemeral=True)
    await bot.bossparty.create(ctx, boss_name)


@_bossparty.command(name='settime', brief='Set the boss party time')
@commands.has_role('Junior')
@app_commands.describe(weekday='day of week: [ mon | tue | wed | thu | fri | sat | sun ]')
@app_commands.describe(hour='hour relative to reset: [0-23]')
@app_commands.describe(minute='minute of the hour: [0-59]')
async def bossparty_settime(ctx, boss_party_role: discord.Role, weekday: str, hour: int, minute: int = 0):
    await ctx.defer(ephemeral=True)
    await bot.bossparty.settime(ctx, boss_party_role, weekday, hour, minute)


@_bossparty.command(name='cleartime', brief='Clear the boss party time')
@commands.has_role('Junior')
async def bossparty_cleartime(ctx, boss_party_role: discord.Role):
    await ctx.defer(ephemeral=True)
    await bot.bossparty.cleartime(ctx, boss_party_role)


@_bossparty.command(name='retire', brief='Retire a party, removing all of its party members')
@commands.has_role('Junior')
async def bossparty_retire(ctx, boss_party_role: discord.Role):
    await bot.bossparty.retire(ctx, boss_party_role)


@_bossparty.command(name='exclusive', brief='Make a party exclusive')
@commands.has_role('Junior')
async def bossparty_exclusive(ctx, boss_party_role: discord.Role):
    await ctx.defer(ephemeral=True)
    await bot.bossparty.exclusive(ctx, boss_party_role)


@_bossparty.command(name='open', brief='Make a party open')
@commands.has_role('Junior')
async def bossparty_open(ctx, boss_party_role: discord.Role):
    await ctx.defer(ephemeral=True)
    await bot.bossparty.open(ctx, boss_party_role)


@_bossparty.command(name='listremake', brief='Remake the boss party list')
@commands.has_role('Junior')
async def bossparty_listremake(ctx):
    await bot.bossparty.listremake(ctx)


@bot.event
async def on_member_remove(member):
    await bot.bossparty.on_member_remove(member)


bot.run(config.BOT_TOKEN)
