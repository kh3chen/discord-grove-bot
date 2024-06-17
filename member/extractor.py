import cv2
import discord
import numpy as np
from fuzzywuzzy import process
from pytesseract import pytesseract

import config


class Result:
    def __init__(self, ign: str, weekly_mission: int, culvert: int, flag: int):
        self.ign = ign
        self.weekly_mission = weekly_mission
        self.culvert = culvert
        self.flag = flag


async def extract(interaction: discord.Interaction, list_of_igns: list[str], custom_ign_map: dict[str, str],
                  byte_images: list[bytes]) -> (
        list[Result], list[list[str]]):
    path_to_tesseract = config.TESSERACT_OCR_PATH
    pytesseract.tesseract_cmd = path_to_tesseract
    text = ""
    i = 0
    # Iterating through every screenshot that was taken and performing
    # image processing to make the images easier to parse
    for byte_image in byte_images:
        img = cv2.imdecode(np.frombuffer(byte_image, dtype=np.uint8), cv2.IMREAD_COLOR)
        # Crop image [y1:y2,x1:x2]
        img = img[152:566, 212:651]
        # Resizing and making the images bigger
        img = cv2.resize(img, None, fx=5, fy=5)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Applying Gaussian blur
        img = cv2.GaussianBlur(img, (3, 3), 0)
        # Using Otsu thresholding to binarize, partitions image into foreground
        # and background
        retval, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        # Applying erosion
        kernel = np.ones((3, 3), np.uint8)
        img = cv2.erode(img, kernel, iterations=1)
        cv2.imwrite('tmp/extracted/processed' + str(i) + '.png', img)
        i += 1
        # Extract text from the images and put it all into one string,
        # I found psm 6 to be the best at parsing the columns and
        # putting the data into rows
        text += pytesseract.image_to_string(img, config='--psm 6 -l eng+ces+fra+spa') + "\n"
        await interaction.followup.send(f'Extracted image {i}')

    # Formatting to prepare to extract data
    data = text.splitlines()

    # Remove empty entries
    data = list(filter(None, data))

    seen_igns = []
    results = []
    errors = []

    # Extracts IGN, Culvert, and Flag Race numbers and compares parsed
    # IGN to the list of IGNs in the guild and finds the most similar match
    for x in range(0, len(data)):
        data[x] = data[x].replace(',', '')
        data[x] = data[x].replace('.', '')
        data[x] = data[x].replace('1]', '0')
        data[x] = data[x].replace('1}', '0')
        data[x] = data[x].split()
        ign = custom_ign_fixes(data[x][0], custom_ign_map)
        match, percent = process.extractOne(ign, list_of_igns)
        # Makes sure there are no dupes, in case multiple screenshots were taken
        # of the same set of members and IGNs match by 70%, if not then send to errors

        if percent >= 70:
            # Appends matched IGNs in format IGN Culvert Flag
            try:
                result = Result(match, int(data[x][-3]), int(data[x][-2]), int(data[x][-1]))
                print(
                    f'Result - match={match}, percent={percent}, ign={ign}, data={data[x]}')
                results.append(result)
                seen_igns.append(match)
                list_of_igns.remove(match)
            except ValueError:
                # Couldn't convert string to int
                print(f'ValueError - match={match}, percent={percent}, data={data[x]}')
                errors.append(data[x])
        # Duped IGNs
        elif match in seen_igns and percent >= 90:
            print(f'Duplicate - match={match}, percent={percent}, data={data[x]}')
            errors.append(['Duplicate'] + data[x])
        else:
            # Put IGNs that couldn't be matched into a list for debugging/manual solving
            print(f'Match error - match={match}, percent={percent}, data={data[x]}')
            errors.append(['Match error'] + data[x])
    return results, errors


def custom_ign_fixes(ign: str, custom_ign_map: dict[str, str]):
    match, percent = process.extractOne(ign, custom_ign_map.keys())
    if percent == 100:
        return custom_ign_map[match]
    else:
        return ign
