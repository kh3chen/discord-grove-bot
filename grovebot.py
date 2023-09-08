import discord
from discord import app_commands
from discord.ext import commands

import announcement
import config
import release
from bossparty import BossParty
from group_boss import BossGroup

MY_GUILD = discord.Object(id=config.GROVE_GUILD_ID)


class GroveBot(commands.Bot):
    bossparty: BossParty

    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def setup_hook(self):
        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
grove_bot = GroveBot(command_prefix='>', intents=intents)
bossparty = BossParty(grove_bot)
boss_group = BossGroup(bossparty)
grove_bot.tree.add_command(BossGroup(grove_bot))


@grove_bot.event
async def on_ready():
    print(f'Logged in as {grove_bot.user} (ID: {grove_bot.user.id})')
    print('------')
    bossparty.on_ready()


@grove_bot.event
async def on_member_remove(member):
    await grove_bot.bossparty.on_member_remove(member)


@grove_bot.command()
async def version(ctx):
    await ctx.send(release.version_name)


@grove_bot.hybrid_command(name='announcement', brief='Sends the weekly Grove announcement')
@commands.has_role('Junior')
@app_commands.describe(emoji='The seasonal Grove tree emoji')
@app_commands.describe(custom_msg_id='The message ID you want to copy for the custom announcement')
async def _announcement(ctx, emoji: str, custom_msg_id: str = None):
    await announcement.send_announcement(grove_bot, ctx, emoji, custom_msg_id)


grove_bot.run(config.BOT_TOKEN)
