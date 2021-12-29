import comicocr
import json
import html
from bs4 import BeautifulSoup
import requests
import os
import logging
from cv2 import imread, VideoCapture
import magic
import re
import multiprocessing as mp

BASEPATH = "output/smbc-comics.com/"

ocr = comicocr.ComicScanner()

class NotAnImageError(Exception):
    pass

class DownloadError(Exception):
    pass

def image_open(path):
    if not is_image(path):
        raise NotAnImageError(path, "is not an image")
    if is_gif(path):
        logging.info(path + " is a GIF, converting...")
        cap = VideoCapture(path)
        _, image = cap.read()
        cap.release()
    else:
        image = imread(path)
    return image

def is_gif(path):
    with open(path, "rb") as file:
        return magic.from_buffer(file.read(2048), mime=True) == "image/gif"

def is_image(path):
    with open(path, "rb") as file:
        return magic.from_buffer(file.read(2048), mime=True)[0:5] == "image"

def main():
    response = requests.get("https://www.smbc-comics.com/comic/archive")
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    items = soup.find_all('option')
    paths = []
    for item in items:
        data = item.get('value')
        if data != "":
            paths.append(item.get('value'))

    if not os.path.exists(BASEPATH):
        logging.info("Base path " + BASEPATH + " does not exist, creating")
        os.makedirs(BASEPATH)

    # Being multiprocessing
    N = int(mp.cpu_count()/1.5)
    with mp.Pool(processes = N) as p:
        p.map(process, [path for path in paths])

def process(path):
    if os.path.exists(BASEPATH+path+"/completed"):
        logging.info("Skipping " + path)
        return

    logging.info("Starting " + path)

    if not os.path.exists(BASEPATH+path):
        logging.info("Comic " + path + " does not exist, creating")
        os.makedirs(BASEPATH+path)

    comic_data = {'url': "https://www.smbc-comics.com/"+path}

    comic = requests.get("https://smbc-comics.com/" + path)
    comic.raise_for_status()

    # Get important comic info
    panels = list(dict.fromkeys(re.findall(r'https\:\/\/www\.smbc-comics\.com\/comics\/.*?\.(?:gif|png|jpg)', comic.text)))
    image_url = panels[0]
    try:
        bonus_url = panels[1]
        comic_data['bonusURL'] = bonus_url
    except IndexError:
        logging.warning("Could not find bonus for " + path)
        open(BASEPATH+path+"/nobonus", "a").close()
        comic_data['bonusURL'] = ""
    title = html.unescape(list(set(re.findall(r'title="(.*)" src', comic.text)))[0])
    comic_data['imageURL'] = image_url
    comic_data['title'] = title

    # Download images if they do not exist
    if not os.path.exists(BASEPATH+path+"/image"):
        image_response = requests.get(image_url)
        if image_response.status_code != 200:
            logging.error("Got response code " + str(image_response.status_code) + ", expected 200")
            raise DownloadError(image_url)
        with open(BASEPATH+path+"/image", "wb") as image_file:
            image_file.write(image_response.content)

    if not os.path.exists(BASEPATH+path+"/bonus") and not os.path.exists(BASEPATH+path+"/nobonus"):
        try:
            bonus_response = requests.get(bonus_url)
            if bonus_response.status_code != 200:
                logging.error("Got response code " + str(bonus_response.status_code) + ", expected 200")
                raise DownloadError(bonus_url)
            with open(BASEPATH+path+"/bonus", "wb") as bonus_file:
                bonus_file.write(bonus_response.content)
        except NotAnImageError:
            logging.warning("Skipping bonus for " + path)
            open(BASEPATH+path+"/nobonus", "a").close()

    # Scan images
    logging.info("Scanning image " + path)
    image = image_open(BASEPATH+path+"/image")
    comic_data['text'] = re.sub('\s+',' ', " ".join(ocr.scan_image(image))) # Scan image, turn result into string, and clean up

    if not os.path.exists(BASEPATH+path+"/nobonus"):
        try:
            bonus_image = image_open(BASEPATH+path+"/bonus")
            comic_data['bonusText'] = re.sub('\s+',' ', " ".join(ocr.scan_image(bonus_image)))
        except NotAnImageError:
            logging.warn("Downloaded file is not an image in " + path)
            open(BASEPATH+path+"/nobonus", "a").close()
            logging.info("Skipping bonus " + path)
            comic_data['bonusText'] = ""
    else:
        logging.info("Skipping bonus " + path)
        comic_data['bonusText'] = ""

    with open(BASEPATH+path+"/metadata.json", "w") as metadata_file:
        metadata_file.write(json.dumps(comic_data))

    # Mark as comepleted
    open(BASEPATH+path+"/completed", "a").close()
    logging.info("Completed " + path)
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
