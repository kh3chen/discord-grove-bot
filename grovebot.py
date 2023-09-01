import discord
from discord import app_commands
from discord.ext import commands
import config
import announcement
import bossparty

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='>', intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    await bot.tree.sync()
    print('Command tree synced.')


@bot.hybrid_command(name='announcement', brief='Sends the weekly Grove announcement')
@commands.has_role('Junior')
@app_commands.describe(emoji='The seasonal Grove tree emoji')
@app_commands.describe(custom_msg_id='The message ID you want to copy for the custom announcement')
async def _announcement(ctx, emoji: str, custom_msg_id: str = None):
    await announcement.send_announcement(bot, ctx, emoji, custom_msg_id)


@bot.hybrid_group(name='bossparty')
async def _bossparty(ctx):
    pass


@_bossparty.command(name='sync')
@commands.has_role('Junior')
async def bossparty_sync(ctx):
    await ctx.defer()
    await bossparty.sync(ctx)


@_bossparty.command(name='add', brief='Add a boss party role to a member')
@commands.has_role('Junior')
async def bossparty_add(ctx, user: discord.Member, boss_party_role: discord.Role, job: str):
    await ctx.defer()
    await bossparty.add(bot, ctx, user, boss_party_role, job)


@_bossparty.command(name='remove', brief='Remove a boss party role from a member')
@commands.has_role('Junior')
async def bossparty_remove(ctx, user: discord.Member, boss_party_role: discord.Role):
    await ctx.defer()
    await bossparty.remove(bot, ctx, user, boss_party_role)


@_bossparty.command(name='create', brief='Create a new boss party')
@commands.has_role('Junior')
async def bossparty_create(ctx, boss_name):
    await ctx.defer()
    await bossparty.create(ctx, boss_name)


@_bossparty.command(name='settime', brief='Set the boss party time')
@commands.has_role('Junior')
@app_commands.describe(weekday='day of week: [ mon | tue | wed | thu | fri | sat | sun ]')
@app_commands.describe(hour='hour relative to reset: [0-23]')
@app_commands.describe(minute='minute of the hour: [0-59]')
async def bossparty_settime(ctx, boss_party_role: discord.Role, weekday: str, hour: int, minute: int = 0):
    await bossparty.settime(bot, ctx, boss_party_role, weekday, hour, minute)


@_bossparty.command(name='retire', brief='Retire a party, removing all of its party members')
@commands.has_role('Junior')
async def bossparty_retire(ctx, boss_party_role: discord.Role):
    await bossparty.retire(bot, ctx, boss_party_role)


@_bossparty.command(name='listremake', brief='Remake the boss party list')
@commands.has_role('Junior')
async def bossparty_listremake(ctx):
    await bossparty.listremake(bot, ctx)


@_bossparty.command(name='posttest', brief='post test')
@commands.has_role('Junior')
async def bossparty_posttest(ctx):
    await bossparty.post_test(bot, ctx)


bot.run(config.BOT_TOKEN)
