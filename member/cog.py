from datetime import datetime, timezone
from functools import reduce

import discord
from dateutil import relativedelta
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

    @app_commands.command(name='retiree', description='Set the Discord member rank to Retiree')
    @app_commands.checks.has_role(config.GROVE_ROLE_ID_JUNIOR)
    async def retiree(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await rank.retiree(interaction, member)


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

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await member.add_roles(self.bot.get_guild(config.GROVE_GUILD_ID).get_role(config.GROVE_ROLE_ID_GROVE))

        created_at_ago = self.relative_delta_text(
            relativedelta.relativedelta(datetime.utcnow().replace(tzinfo=timezone.utc), member.created_at))

        # Send to log channel
        member_join_remove_channel = self.bot.get_channel(config.GROVE_CHANNEL_ID_MEMBER_JOIN_LEAVE)
        join_embed = discord.Embed(title='Member joined',
                                   description=f'{member.mention}'
                                               f'\ncreated {created_at_ago} ago',
                                   colour=int('0x53DDAC', 16))
        join_embed.set_author(name=member.name, icon_url=member.avatar.url)
        await member_join_remove_channel.send(embed=join_embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Send to log channel
        member_join_remove_channel = self.bot.get_channel(config.GROVE_CHANNEL_ID_MEMBER_JOIN_LEAVE)
        member_roles = reduce(lambda acc, val: acc + (" " if acc else "") + val,
                              map(lambda role: role.mention, sorted(member.roles[1:], key=lambda role: role.position,
                                                                    reverse=True)))  # Remove @everyone, sort by position descending

        joined_at_ago = self.relative_delta_text(
            relativedelta.relativedelta(datetime.utcnow().replace(tzinfo=timezone.utc), member.joined_at))

        join_embed = discord.Embed(title='Member left',
                                   description=f'{member.mention} joined {joined_at_ago} ago'
                                               f'\n**Roles:** {member_roles}',
                                   colour=int('0xFFF5AF', 16))
        join_embed.set_author(name=member.name, icon_url=member.avatar.url)
        await member_join_remove_channel.send(embed=join_embed)

    @staticmethod
    def relative_delta_text(delta: relativedelta):
        if delta.years > 0:
            return f'{delta.years} year{"s"[:delta.years ^ 1]}' + (
                f', {delta.months} month{"s"[:delta.months ^ 1]}' if delta.months > 0 else '') + (
                f', {delta.days} day{"s"[:delta.days ^ 1]}' if delta.days > 0 else '')
        elif delta.months > 0:
            return f'{delta.months} month{"s"[:delta.months ^ 1]}' + (
                f', {delta.days} day{"s"[:delta.days ^ 1]}' if delta.days > 0 else '')
        elif delta.days >= 7:
            return f'{delta.days} day{"s"[:delta.days ^ 1]}'
        elif delta.days > 0:
            return f'{delta.days} day{"s"[:delta.days ^ 1]}' + (
                f', {delta.hours} hour{"s"[:delta.hours ^ 1]}' if delta.hours > 0 else '')
        elif delta.hours > 0:
            return f'{delta.hours} hour{"s"[:delta.hours ^ 1]}' + (
                f', {delta.minutes} minute{"s"[:delta.minutes ^ 1]}' if delta.minutes > 0 else '')
        elif delta.minutes > 0:
            return f'{delta.minutes} minute{"s"[:delta.minutes ^ 1]}' + (
                f', {delta.seconds} second{"s"[:delta.seconds ^ 1]}' if delta.seconds > 0 else '')
        else:
            return f'{delta.seconds} second{"s"[:delta.seconds ^ 1]}'


async def setup(bot):
    await bot.add_cog(MemberCog(bot))
