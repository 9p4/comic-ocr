from typing import Iterable
from shapely.geometry import Polygon
import pytesseract
import argparse
import cv2
from imutils.object_detection import non_max_suppression
import numpy as np
from textblob import TextBlob

TESSCONFIG = "-c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ\\\'\!\?\ \. --oem 1"

class ComicScanner():
    def __init__(self) -> None:
        self.net = cv2.dnn.readNet("frozen_east_text_detection.pb")

    def scan_image(self, image) -> Iterable:
        # https://www.pyimagesearch.com/2018/08/20/opencv-text-detection-east-text-detector/
        orig = image.copy()
        (H, W) = image.shape[:2]
        # set the new width and height and then determine the ratio in change
        # for both the width and height
        (newW, newH) = (W>>5<<5, H>>5<<5)
        rW = W / float(newW)
        rH = H / float(newH)
        
        img = cv2.resize(image, (newW, newH))
        (H, W) = img.shape[:2]
        # define the two output layer names for the EAST detector model that
        # we are interested -- the first is the output probabilities and the
        # second can be used to derive the bounding box coordinates of text
        layerNames = [
            "feature_fusion/Conv_7/Sigmoid",
            "feature_fusion/concat_3"]

        # construct a blob from the image and then perform a forward pass of
        # the model to obtain the two output layer sets
        blob = cv2.dnn.blobFromImage(img, 1.0, (W, H),
            (123.68, 116.78, 103.94), swapRB=True, crop=False)
        self.net.setInput(blob)
        (scores, geometry) = self.net.forward(layerNames)
        # grab the number of rows and columns from the scores volume, then
        # initialize our set of bounding box rectangles and corresponding
        # confidence scores
        (numRows, numCols) = scores.shape[2:4]
        rects = []
        confidences = []
        # loop over the number of rows
        for y in range(0, numRows):
            # extract the scores (probabilities), followed by the geometrical
            # data used to derive potential bounding box coordinates that
            # surround text
            scoresData = scores[0, 0, y]
            xData0 = geometry[0, 0, y]
            xData1 = geometry[0, 1, y]
            xData2 = geometry[0, 2, y]
            xData3 = geometry[0, 3, y]
            anglesData = geometry[0, 4, y]
        	# loop over the number of columns
            for x in range(0, numCols):
                # if our score does not have sufficient probability, ignore it
                if scoresData[x] < 0.5:
                    continue
                # compute the offset factor as our resulting feature maps will
                # be 4x smaller than the input image
                (offsetX, offsetY) = (x * 4.0, y * 4.0)
                # extract the rotation angle for the prediction and then
                # compute the sin and cosine
                angle = anglesData[x]
                cos = np.cos(angle)
                sin = np.sin(angle)
                # use the geometry volume to derive the width and height of
                # the bounding box
                h = 1.2*(xData0[x] + xData2[x])
                w = 1.2*(xData1[x] + xData3[x])
                # compute both the starting and ending (x, y)-coordinates for
                # the text prediction bounding box
                endX = int(offsetX + (cos * xData1[x]) + (sin * xData2[x]))
                endY = int(offsetY - (sin * xData1[x]) + (cos * xData2[x]))
                startX = int(endX - w)
                startY = int(endY - h)
                # add the bounding box coordinates and probability score to
                # our respective lists
                rects.append((startX, startY, endX, endY))
                confidences.append(scoresData[x])
        # apply non-maxima suppression to suppress weak, overlapping bounding
        # boxes
        boxes = non_max_suppression(np.array(rects), probs=confidences)
        # loop over the bounding boxes
        clusters = []
        for (startX, startY, endX, endY) in boxes:
            # scale the bounding box coordinates based on the respective
            # ratios
            startX = int(startX * rW)
            startY = int(startY * rH)
            endX = int(endX * rW)
            endY = int(endY * rH)
            box = (startX, startY, endX, endY)
            matched = False
            for i in range(0, len(clusters)):
                if (rect_overlaps(box, clusters[i])):
                    matched = True
                    clusters[i] = (
                        min(box[0], clusters[i][0]),
                        min(box[1], clusters[i][1]),
                        max(box[2], clusters[i][2]),
                        max(box[3], clusters[i][3])
                    )
            if not matched:
                clusters.append(box)

        # Remove duplicate clusters
        for _ in range(0,1):
            finalClusters = []
            for cluster in clusters:
                matched = False
                for i in range(0, len(finalClusters)):
                    if (rect_overlaps(cluster, finalClusters[i])):
                        matched = True
                        finalClusters[i] = (
                            min(cluster[0], finalClusters[i][0]),
                            min(cluster[1], finalClusters[i][1]),
                            max(cluster[2], finalClusters[i][2]),
                            max(cluster[3], finalClusters[i][3])
                        )
                if not matched:
                    finalClusters.append(cluster)
            clusters = finalClusters

        # Final cleanup
        suppressedClusters = non_max_suppression(np.array(finalClusters))

        for (startX, startY, endX, endY) in suppressedClusters:
            cropStartX = int(max(startX-10, 0))
            cropStartY = int(max(startY-10, 0))            
            cropEndX = int(min(endX+10,W*rW))
            cropEndY = int(min(endY+10,H*rH))
            cropped = orig[cropStartY:cropEndY, cropStartX:cropEndX]
            text = str(TextBlob("".join([c if ord(c) < 128 else "" for c in pytesseract.image_to_string(cropped, lang="eng", config=TESSCONFIG)]).strip().replace("[", "I").replace("\\", "l").replace("/","i").lower()).correct())
            yield text

def rect_overlaps(r1,r2):
    poly1 = Polygon([[r1[0], r1[1]], [r1[0], r1[3]], [r1[2], r1[1]], [r1[2], r1[3]]])
    poly2 = Polygon([[r2[0], r2[1]], [r2[0], r2[3]], [r2[2], r2[1]], [r2[2], r2[3]]])
    return poly1.distance(poly2) < 5

def main():
    parser = argparse.ArgumentParser(description='Comic OCR processor')
    parser.add_argument('paths', metavar='path', type=str, nargs='+',
                        help='paths to images to scan')

    args = parser.parse_args()

    for path in args.paths:
        try:
            img = cv2.imread(path)
        except:
            print("Path does not exist, or is not a valid image")
            break
        for text in scan_image(img):
            print(text)

if __name__ == "__main__":
    main()
