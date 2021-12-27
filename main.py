from typing import Iterable
import pytesseract
import argparse
import cv2
from textblob import TextBlob

def scanImage(img) -> Iterable:
    # https://www.geeksforgeeks.org/text-detection-and-extraction-using-opencv-and-ocr
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
     
    ret, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)
    rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 18))
     
    dilation = cv2.dilate(thresh1, rect_kernel, iterations = 1)
     
    contours, hierarchy = cv2.findContours(dilation, cv2.RETR_EXTERNAL,
                                                     cv2.CHAIN_APPROX_NONE)
    im2 = img.copy()
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
         
        rect = cv2.rectangle(im2, (x, y), (x + w, y + h), (0, 255, 0), 2)
         
        cropped = im2[y:y + h, x:x + w]
         
        yield TextBlob(pytesseract.image_to_string(cropped).lower()).correct()

def main():
    parser = argparse.ArgumentParser(description='Comic OCR processor')
    parser.add_argument('paths', metavar='path', type=str, nargs='+',
                        help='paths to images to scan')

    args = parser.parse_args()

    for path in args.paths:
        try:
            img = cv2.imread(path)
        except:
            print("Path does not exist, or is not an image")
            break
        for text in scanImage(img):
            print(text)

if __name__ == "__main__":
    main()
