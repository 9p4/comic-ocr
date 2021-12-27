import os
import json

BASEDIR = "output/smbc-comics.com/comic/"

def main():
    comics = os.listdir(BASEDIR)
    data = []
    for comic in comics:
        comicData = {}
        comicData['title'] = comic
        with open(BASEDIR+comic+"/image.txt", "r") as file:
            comicData['comic'] = file.read().replace("\n", " ").replace("\x0c", "")
            file.close()
        if os.path.exists(BASEDIR+comic+"/bonus.txt"):
            with open(BASEDIR+comic+"/bonus.txt", "r") as file:
                comicData['bonus'] = file.read().replace("\n", " ").replace("\x0c", "")
                file.close()
        else:
            comicData['bonus'] = ""
        with open(BASEDIR+comic+"/title.txt", "r") as file:
            comicData['alt'] = file.read()
            file.close()
        data.append(comicData)

    with open("output.js", "w") as file:
        file.write("const list=")
        file.write(json.dumps(data))
        file.write(";")
        file.close()

if __name__ == "__main__":
    main()
