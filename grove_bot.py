import discord
from discord import app_commands
from discord.ext import commands
import config
import announcement
import boss_party

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


@bot.hybrid_group(name="boss_party")
async def _boss_party(ctx):
    pass


@_boss_party.command(name='sync')
async def boss_party_sync(ctx):
    await ctx.defer()
    await boss_party.sync(ctx)


@_boss_party.command(name='add', brief='Add a boss party role to a member')
# @commands.group(name='boss_party')
@commands.has_role('Junior')
async def boss_party_add(ctx, user: discord.Member, boss_party_role: discord.Role, job: str):
    await ctx.defer()
    await boss_party.add(ctx, user, boss_party_role, job)


@_boss_party.command(name='remove', brief='Remove a boss party role from a member')
async def boss_party_remove(ctx, user: discord.Member, boss_party_role: discord.Role):
    await ctx.defer()
    await boss_party.remove(ctx, user, boss_party_role)


@_boss_party.command(name='create', brief='Create a new boss party')
async def boss_party_create(ctx, boss_name):
    await ctx.defer()
    await boss_party.create(ctx, boss_name)


@_boss_party.command(name='set_time', brief='Set the boss party time')
@app_commands.describe(weekday='day of week: [ mon | tue | wed | thu | fri | sat | sun ]')
@app_commands.describe(hour='hour relative to reset: [0-23]')
@app_commands.describe(minute='minute of the hour: [0-59]')
async def boss_party_set_time(ctx, boss_party_role: discord.Role, weekday: str, hour: int, minute: int = 0):
    await boss_party.set_time(bot, ctx, boss_party_role, weekday, hour, minute)


@_boss_party.command(name='retire', brief='Retire a party, removing all of its party members')
async def boss_party_retire(ctx, boss_party_role: discord.Role):
    await boss_party.retire(bot, ctx, boss_party_role)


@_boss_party.command(name='list_remake', brief='Remake the boss party list')
async def boss_party_list_make(ctx):
    await boss_party.list_remake(bot, ctx)


@_boss_party.command(name='post_test', brief='post test')
async def boss_party_post_test(ctx):
    await boss_party.post_test(bot, ctx)


bot.run(config.BOT_TOKEN)
