import comicocr
from bs4 import BeautifulSoup
import requests
import os
import logging
from cv2 import imread, VideoCapture
import magic
from tqdm import tqdm

BASEPATH = "output/smbc-comics.com/"

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
            logging.debug("Adding item " + data)

    length = len(paths)

    if not os.path.exists(BASEPATH):
        logging.info("Base path " + BASEPATH + " does not exist, creating")
        os.makedirs(BASEPATH)

    for i in tqdm(range(length)):
        path = paths[i]
        if not os.path.exists(BASEPATH+path):
            logging.info("Comic " + path + " does not exist, creating")
            os.makedirs(BASEPATH+path)
        comic = requests.get("https://smbc-comics.com/" + path)
        logging.debug(comic.text)
        comic.raise_for_status()
        soup = BeautifulSoup(comic.content, 'html.parser')
        image = soup.find(id='cc-comic')
        if not os.path.exists(BASEPATH+path+"/title.txt"):
            with open(BASEPATH+path+"/title.txt", "w") as file:
                alt = image.get("title")
                logging.info(alt)
                file.write(alt)
                file.close()
        else:
            logging.info("Skipping title text")

        if not os.path.exists(BASEPATH+path+"/image"):
            logging.info("Image for " + path + " doesn't exist, downloading")
            img = requests.get(image.get("src"))
            img.raise_for_status()
            with open(BASEPATH+path+"/image", "wb") as file:
                file.write(img.content)
                file.close()
        else:
            logging.info("Image already exists")

        if not os.path.exists(BASEPATH+path+"/bonus") and not os.path.exists(BASEPATH+path+"/nobonus"):
            bonus_path = soup.find(id="aftercomic").findChildren()[0].get("src")
            bonus = requests.get(bonus_path)
            if bonus.status_code == 404:
                open(BASEPATH+path+"/nobonus", "a").close()
            else:
                bonus.raise_for_status()
                with open(BASEPATH+path+"/bonus", "wb") as file:
                    file.write(bonus.content)
                    file.close()
        else:
            logging.info("Skipping bonus")



        if not os.path.exists(BASEPATH+path+"/image.txt"):
            logging.info("Scanning image " + path)
            imagetype = magic.from_buffer(open(BASEPATH+path+"/image", "rb").read(2048), mime=True)
            logging.debug(imagetype)
            if imagetype == "image/gif":
                logging.info("Image is a GIF, converting...")
                cap = VideoCapture(BASEPATH+path+"/image")
                ret, image = cap.read()
                cap.release()
            else:
                image = imread(BASEPATH+path+"/image")
            with open(BASEPATH+path+"/image.txt", "w") as file:
                file.writelines(comicocr.scan_image(image))
        else:
            logging.info("Skipping image " + path)

        if not os.path.exists(BASEPATH+path+"/bonus.txt") and not os.path.exists(BASEPATH+path+"/nobonus"):
            imagetype = magic.from_buffer(open(BASEPATH+path+"/bonus", "rb").read(2048), mime=True)
            logging.debug(imagetype)
            if imagetype == "image/gif":
                logging.info("Image is a GIF, converting...")
                cap = VideoCapture(BASEPATH+path+"/bonus")
                ret, image = cap.read()
                cap.release()
            else:
                image = imread(BASEPATH+path+"/bonus")
            with open(BASEPATH+path+"/bonus.txt", "w") as file:
                file.writelines(comicocr.scan_image(image))
        else:
            logging.info("Skipping bonus " + path)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
