import discord
from discord.ext import commands

import config
import grove_config
from utils import version

grove_config.set_configs()
MY_GUILD = discord.Object(id=config.GROVE_GUILD_ID)


class GroveBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def setup_hook(self):
        await self.load_extension('member.cog')
        await self.load_extension('bossing.cog')
        await self.load_extension('absence.cog')
        await self.load_extension('birthday.cog')
        await self.load_extension('culvert.cog')
        print('Cogs loaded.')
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)
        print('Command tree synced.')


grove_bot_intents = discord.Intents.default()
grove_bot_intents.members = True
grove_bot_intents.message_content = True
grove_bot_intents.reactions = True
grove_bot = GroveBot(command_prefix='>', intents=grove_bot_intents)


@grove_bot.event
async def on_ready():
    print(f'Logged in as {grove_bot.user} (ID: {grove_bot.user.id})')
    print('------')


@grove_bot.command(name='version')
async def _version(ctx):
    await ctx.send(version.version_name)


@grove_bot.command(name='batch-add-role')
async def add_role(ctx, role: discord.Role, *members: discord.Member):
    for member in members:
        await member.add_roles(role)
        await ctx.send(f'Added {role.name} to {member.name}.')


@add_role.error
async def add_role_error(ctx, error):
    await ctx.send('Error - Command format must be `>add-role [role] [members]`.')


grove_bot.run(config.BOT_TOKEN)
