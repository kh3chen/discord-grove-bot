import discord
from discord.ext import commands

import config
from utils import version

MY_GUILD = discord.Object(id=config.GROVE_GUILD_ID)


class GroveBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def setup_hook(self):
        await self.load_extension('announcement.cog')
        await self.load_extension('bossing.cog')
        print('Cogs loaded.')
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)
        print('Command tree synced.')


grove_bot_intents = discord.Intents.default()
grove_bot_intents.members = True
grove_bot_intents.message_content = True
grove_bot = GroveBot(command_prefix='>', intents=grove_bot_intents)


@grove_bot.event
async def on_ready():
    print(f'Logged in as {grove_bot.user} (ID: {grove_bot.user.id})')
    print('------')


@grove_bot.command(name='version')
async def _version(ctx):
    await ctx.send(version.version_name)


grove_bot.run(config.BOT_TOKEN)
