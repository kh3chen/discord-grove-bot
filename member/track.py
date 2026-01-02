import discord

from member import sheets, sheets_shrub, common, extractor
from member.sheets_shrub import WeeklyParticipation


class Character:
    def __init__(self, ign: str, discord_mention: str):
        self.ign = ign
        self.discord_mention = discord_mention

    def __str__(self):
        return str([self.ign, self.discord_mention])

    def __repr__(self):
        return self.__str__()


async def track_grove(interaction: discord.Interaction, message_ids: list[int]):
    thursday_string = common.thursday().strftime('%Y-%m-%d')
    characters = []
    for sheets_member in sheets.get_unsorted_member_participation():
        for ign in sheets_member.grove_igns.split('\n'):
            characters.append(Character(ign, sheets_member.discord_mention))
    print(f'Characters: {characters}')

    tracks, errors = await __track(interaction, message_ids, thursday_string, characters, 'Grove')

    sheets.append_tracks(tracks)

    for character in characters:
        if character.ign != '':
            errors.append(['Missing', thursday_string, character.discord_mention, character.ign, 'Grove'])
    sheets.append_errors(errors)

    await interaction.followup.send(f'### Tracking data saved for Grove\nSuccess: {len(tracks)}\nError: {len(errors)}')

    week_header = __update_weekly_participation(tracks)
    await interaction.followup.send(f'{week_header} Grove tracking complete!')


async def track_shrub(interaction: discord.Interaction, message_ids: list[int]):
    thursday_string = common.thursday().strftime('%Y-%m-%d')
    characters = []
    for sheets_member in sheets_shrub.get_unsorted_shrub_participation():
        for ign in sheets_member.mule_igns.split('\n'):
            characters.append(Character(ign, sheets_member.discord_mention))
    print(f'Characters: {characters}')

    tracks, errors = await __track(interaction, message_ids, thursday_string, characters, "Shrub")
    sheets.append_tracks(tracks)
    sheets.append_errors(errors)

    await interaction.followup.send(
        f'### Tracking data saved for Shrub\nSuccess: {len(tracks)}\nError: {len(errors)}')

    week_header = __update_shrub_participation(tracks)
    await interaction.followup.send(f'{week_header} Shrub tracking complete!')


async def __track(interaction: discord.Interaction, message_ids: list[int], day_string: str,
                  characters: list[Character], guild: str):
    attachments = []
    try:
        for message_id in message_ids:
            message = await interaction.channel.fetch_message(message_id)
            attachments += message.attachments
    except Exception as e:
        await interaction.followup.send(f'Error - {e}')
    byte_images = []
    for attachment in attachments:
        byte_images.append(await attachment.read())
    await interaction.followup.send(f'Tracking {len(byte_images)} screenshots. This might take a few minutes.')
    custom_ign_map = sheets.get_custom_ign_mapping()
    results, errors = await extractor.extract(interaction, list(map(lambda character: character.ign, characters)),
                                              custom_ign_map, byte_images)
    tracks = []
    for result in results:
        try:
            character = next(character for character in characters if result.matched_ign == character.ign)
            track = sheets.Track(day_string, character.discord_mention, result.matched_ign, guild,
                                 result.weekly_mission, result.culvert, result.flag, result.raw_ign(),
                                 result.matched_percent)
            tracks.append(track)
            characters.remove(character)
        except StopIteration:
            # This should already be captured in errors during extraction
            pass

    errors = list(map(lambda error: [error[0], day_string, '', '', guild] + error[1:], errors))
    return tracks, errors


def __update_weekly_participation(tracks: list[sheets.Track]):
    guild_week = common.guild_week()
    thursday_string = common.thursday().strftime('%Y-%m-%d')
    if not sheets.is_valid(guild_week, thursday_string):
        sheets.insert_weekly_participation_column(f'Week {guild_week}\n{thursday_string}')

    mp_list = sheets.get_unsorted_member_participation()
    scores = sheets.get_weekly_participation()
    if scores is None:
        scores = [None] * len(mp_list)
    else:
        scores = scores + [None] * (len(mp_list) - len(scores))
    for x in range(len(mp_list)):
        member = mp_list[x]
        for track in tracks:
            if member.discord_mention == track.discord_mention:
                new_score = track.mission / 2
                if track.culvert > 0:
                    new_score += 10
                if track.flag > 0:
                    new_score += 10
                if scores[x] is None or new_score > scores[x]:
                    scores[x] = new_score

    sheets.update_weekly_participation(scores)
    return f'Week {guild_week} - {thursday_string}'


def __update_shrub_participation(tracks: list[sheets.Track]):
    guild_week = common.guild_week()
    thursday_string = common.thursday().strftime('%Y-%m-%d')
    if not sheets_shrub.is_valid(guild_week, thursday_string):
        sheets_shrub.insert_weekly_participation_columns(
            f'Week {guild_week}\n{thursday_string}')

    wp_list = []
    for member in sheets_shrub.get_unsorted_shrub_participation():
        participation = WeeklyParticipation()
        wp_list.append(participation)
        for track in tracks:
            if (member.discord_mention == track.discord_mention
                    and track.mission > 0):  # Only count if the boss mule is active
                participation.add(track.ign, track.culvert, track.flag)

    sheets_shrub.update_weekly_participation(wp_list)
    return f'Week {guild_week} - {thursday_string}'
