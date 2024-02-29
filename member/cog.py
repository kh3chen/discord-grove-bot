import discord
from discord import app_commands
from discord.ext import commands

import config
from member import leaderboard, rank


class ModRankGroup(app_commands.Group, name='mod-rank', description='Mod member rank commands'):
    @app_commands.command(name='spirit', description='Set the Discord member rank to Spirit')
    @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
    async def spirit(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await rank.spirit(interaction, member)

    @app_commands.command(name='tree', description='Set the Discord member rank to Tree')
    @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
    async def tree(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await rank.tree(interaction, member)

    @app_commands.command(name='sapling', description='Set the Discord member rank to Sapling')
    @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
    async def sapling(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await rank.sapling(interaction, member)

    @app_commands.command(name='moss', description='Set the Discord member rank to Moss')
    @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
    async def moss(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await rank.moss(interaction, member)

    @app_commands.command(name='guest', description='Set the Discord member rank to Guest')
    @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
    async def guest(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await rank.guest(interaction, member)


class MemberCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    mod_rank = ModRankGroup()

    @app_commands.command(name='mod-leaderboard', description='Sends the weekly Grove leaderboard')
    @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
    @app_commands.describe(emoji='The seasonal Grove tree emoji')
    async def leaderboard(self, interaction, emoji: str):
        await interaction.response.defer()
        await leaderboard.send_leaderboard(self.bot, interaction, emoji)


async def setup(bot):
    await bot.add_cog(MemberCog(bot))
