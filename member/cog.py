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

        # Send to log channel
        member_join_remove_channel = self.bot.get_channel(config.GROVE_CHANNEL_ID_MEMBER_JOIN_LEAVE)
        join_embed = discord.Embed(title='Member joined',
                                   description=f'{member.mention}'
                                               f'\ncreated <t:{int(member.created_at.timestamp())}:F> <t:{int(member.created_at.timestamp())}:R>',
                                   colour=int('0x53DDAC', 16))
        join_embed.set_author(name=member.name, icon_url=member.avatar.url)
        await member_join_remove_channel.send(embed=join_embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Send to log channel
        member_join_remove_channel = self.bot.get_channel(config.GROVE_CHANNEL_ID_MEMBER_JOIN_LEAVE)
        member_roles = reduce(lambda acc, val: acc + (" " if acc else "") + val,
                              list(map(lambda role: role.mention, member.roles))[1:])  # Remove @everyone

        diff = relativedelta.relativedelta(member.joined_at, datetime.utcnow().replace(tzinfo=timezone.utc))

        if diff.years > 0:
            member_joined_ago = f'{diff.years} year{"s"[:diff.years ^ 1]}' + (
                f', {diff.months} month{"s"[:diff.months ^ 1]}' if diff.months > 0 else '') + (
                                    f', {diff.days} day{"s"[:diff.days ^ 1]}' if diff.days > 0 else '')
        elif diff.months > 0:
            member_joined_ago = f'{diff.months} month{"s"[:diff.months ^ 1]}' + (
                f', {diff.days} day{"s"[:diff.days ^ 1]}' if diff.days > 0 else '')
        elif diff.days >= 7:
            member_joined_ago = f'{diff.days} day{"s"[:diff.days ^ 1]}'
        elif diff.days > 0:
            member_joined_ago = f'{diff.days} day{"s"[:diff.days ^ 1]}' + (
                f', {diff.hours} hour{"s"[:diff.hours ^ 1]}' if diff.hours > 0 else '')
        elif diff.hours > 0:
            member_joined_ago = f'{diff.hours} hour{"s"[:diff.hours ^ 1]}' + (
                f', {diff.minutes} minute{"s"[:diff.minutes ^ 1]}' if diff.minutes > 0 else '')
        elif diff.minutes > 0:
            member_joined_ago = f'{diff.minutes} minute{"s"[:diff.minutes ^ 1]}' + (
                f', {diff.seconds} second{"s"[:diff.seconds ^ 1]}' if diff.seconds > 0 else '')
        else:
            member_joined_ago = f'{diff.seconds} second{"s"[:diff.seconds ^ 1]}'

        join_embed = discord.Embed(title='Member left',
                                   description=f'{member.mention} joined {member_joined_ago} ago'
                                               f'\n**Roles:** {member_roles}',
                                   colour=int('0xFFF5AF', 16))
        join_embed.set_author(name=member.name, icon_url=member.avatar.url)
        await member_join_remove_channel.send(embed=join_embed)


async def setup(bot):
    await bot.add_cog(MemberCog(bot))
