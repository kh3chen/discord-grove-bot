import discord
from discord import app_commands
from discord.ext import commands

import config
from announcement import announcement
from bossing.bossing import Bossing
from utils import version

MY_GUILD = discord.Object(id=config.GROVE_GUILD_ID)


class GroveBot(commands.Bot):
    boss_commands: Bossing

    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def setup_hook(self):
        await self.load_extension('bossing.cog')
        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)


grove_bot_intents = discord.Intents.default()
grove_bot_intents.members = True
grove_bot_intents.message_content = True
grove_bot = GroveBot(command_prefix='>', intents=grove_bot_intents)

@grove_bot.event
async def on_ready():
    print(f'Logged in as {grove_bot.user} (ID: {grove_bot.user.id})')
    print('------')


@grove_bot.command()
async def version(ctx):
    await ctx.send(version.version_name)


@grove_bot.hybrid_command(name='announcement', brief='Sends the weekly Grove announcement')
@commands.has_role('Junior')
@app_commands.describe(emoji='The seasonal Grove tree emoji')
@app_commands.describe(custom_msg_id='The message ID you want to copy for the custom announcement')
async def _announcement(ctx, emoji: str, custom_msg_id: str = None):
    await announcement.send_announcement(grove_bot, ctx, emoji, custom_msg_id)

grove_bot.run(config.BOT_TOKEN)
