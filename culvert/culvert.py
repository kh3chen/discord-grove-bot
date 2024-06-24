import discord

import maplestorygg.character
from culvert import sheets


async def culvert(interaction: discord.Interaction, ign: str):
    try:
        # First check if we have records for this ign
        culvert_max = next(
            culvert_max for culvert_max in sheets.get_culvert_max_scores() if culvert_max.ign.lower() == ign.lower())

        maple_character = maplestorygg.character.get_character(ign)
        culvert_embed = discord.Embed(title=maple_character.name,
                                      colour=int('0x53DDAC', 16))
        culvert_embed.set_author(name='Grove Culvert Stats')
        culvert_embed.add_field(name='Class', value=maple_character.job)
        culvert_embed.add_field(name='Level', value=f'{maple_character.level} ({maple_character.exp_percent}%)')
        if maple_character.legion_level > 0:
            culvert_embed.add_field(name='Legion Level', value=maple_character.legion_level)
        culvert_embed.set_thumbnail(url=maple_character.character_image_url)

        culvert_embed.add_field(name='All-Time High Score', value=f'{culvert_max.score:,}', inline=False)

        for culvert_weeks in sheets.get_culvert_weeks_scores():
            if culvert_weeks.ign.lower() == ign.lower():
                for date in culvert_weeks.scores.keys():
                    score = culvert_weeks.scores[date]
                    if score is not None:
                        culvert_embed.add_field(name=date, value=f'{score:,}')
                break

        await interaction.followup.send(embed=culvert_embed)
    except StopIteration:
        await interaction.followup.send(f'Error - Unable to find Culvert data for `{ign}`')
