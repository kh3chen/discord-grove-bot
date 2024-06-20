import requests

endpoint = "https://api.maplestory.gg/v2/public/character/gms/"


class MapleCharacter:
    def __init__(self, name: str, job: str, level: int, exp_percent: float, legion_level: int,
                 character_image_url: str):
        self.name = name
        self.job = job
        self.level = level
        self.exp_percent = exp_percent
        self.legion_level = legion_level
        self.character_image_url = character_image_url


def get_character(ign: str):
    response = requests.get(endpoint + ign)
    json = response.json()
    return MapleCharacter(name=json['CharacterData']['Name'],
                          job=json['CharacterData']['Class'],
                          level=json['CharacterData']['Level'],
                          exp_percent=json['CharacterData']['EXPPercent'],
                          legion_level=json['CharacterData']['LegionLevel'],
                          character_image_url=json['CharacterData']['CharacterImageURL'])
