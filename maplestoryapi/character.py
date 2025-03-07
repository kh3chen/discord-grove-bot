import requests

maplestorygg_endpoint = "https://api.maplestory.gg/v2/public/character/gms/"
nexon_legion_endpoint = "https://www.nexon.com/api/maplestory/no-auth/ranking/v2/na?type=legion&id=45&character_name="


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
    response = requests.get(maplestorygg_endpoint + ign)
    try:
        json = response.json()
        if 'CharacterData' in json:
            return MapleCharacter(name=json['CharacterData']['Name'],
                                  job=json['CharacterData']['Class'],
                                  level=json['CharacterData']['Level'],
                                  exp_percent=json['CharacterData']['EXPPercent'],
                                  legion_level=json['CharacterData']['LegionLevel'],
                                  character_image_url=json['CharacterData']['CharacterImageURL'])
    except:
        return MapleCharacter(ign, '', 0, 0, 0, '')


def get_legion(ign: str):
    response = requests.get(maplestorygg_endpoint + ign)
    try:
        json = response.json()
        if 'CharacterData' in json and json['CharacterData']['LegionLevel'] > 0:
            return json['CharacterData']['LegionLevel']
    except:
        pass

    response = requests.get(nexon_legion_endpoint + ign)
    try:
        # Special characters don't work for maplestorygg API, try the Nexon API.
        # Nexon API is rate limited, so we want to avoid using it as much as possible.
        json = response.json()
        print(f'{ign}: {json}')
        if json['totalCount'] != 1:
            return 0
        return json['ranks'][0]['legionLevel']
    except:
        return 0
