import discord

from member import sheets, common, extractor


class Character:
    def __init__(self, ign: str, discord_mention: str):
        self.ign = ign
        self.discord_mention = discord_mention

    def __str__(self):
        return str([self.ign, self.discord_mention])

    def __repr__(self):
        return self.__str__()


async def track(interaction: discord.Interaction, message_ids: list[int]):
    sunday_string = common.sunday().strftime('%Y-%m-%d')
    characters = []
    for sheets_member in sheets.get_unsorted_member_participation():
        for ign in sheets_member.grove_igns.split('\n'):
            characters.append(Character(ign, sheets_member.discord_mention))
    print(f'Characters: {characters}')

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
    try:
        results, errors = extractor.extract(list(map(lambda character: character.ign, characters)), custom_ign_map,
                                            byte_images)
        tracks = []
        for result in results:
            try:
                character = next(character for character in characters if result.ign == character.ign)
                track = sheets.Track(sunday_string, character.discord_mention,
                                     result.ign,
                                     result.weekly_mission, result.culvert, result.flag)
                tracks.append(track)
                characters.remove(character)
            except StopIteration:
                pass

        sheets.append_tracks(tracks)

        errors = list(map(lambda error: [sunday_string] + error, errors))
        for character in characters:
            if character.ign != '':
                errors.append([sunday_string, character.ign, character.discord_mention, 'MISSING'])
        sheets.append_errors(errors)

        await interaction.followup.send(f'Tracking data saved\nSuccess: {len(tracks)}\nError: {len(errors)}')

        week_header = update_weekly_participation(tracks)
        await interaction.followup.send(f'{week_header} tracking complete!')
    except Exception as e:
        await interaction.followup.send(f'Error - {e}')


def update_weekly_participation(tracks: list[sheets.Track]):
    guild_week = common.guild_week()
    sunday_string = common.sunday().strftime('%Y-%m-%d')
    if not sheets.is_valid(guild_week, sunday_string):
        sheets.insert_weekly_participation_column(f'Week {guild_week}\n{sunday_string}')

    mp_list = sheets.get_unsorted_member_participation()
    scores = sheets.get_weekly_participation()
    scores = scores + [None] * (len(mp_list) - len(scores))
    for x in range(len(mp_list)):
        member = mp_list[x]
        score = scores[x]
        for track in tracks:
            if member.discord_mention == track.discord_mention:
                new_score = track.mission
                if track.culvert > 0:
                    new_score += 10
                if track.flag > 0:
                    new_score += 10
                if not score or new_score > score:
                    scores[x] = new_score
                tracks.remove(track)

    sheets.update_weekly_participation(scores)
    return f'Week {guild_week} {sunday_string}'
