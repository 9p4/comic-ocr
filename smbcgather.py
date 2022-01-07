import os
import json

BASEDIR = "output/smbc-comics.com/comic/"

def main():
    comics = os.listdir(BASEDIR)
    data = []
    for comic in comics:
        if not os.path.exists(BASEDIR+comic+"/completed"):
            continue
        with open(BASEDIR+comic+"/metadata.json", "r") as metadata_file:
            data.append(json.loads(metadata_file.read()))

    with open("data.js", "w") as file:
        file.write("const list=")
        file.write(json.dumps(data))
        file.write(";")

if __name__ == "__main__":
    main()
