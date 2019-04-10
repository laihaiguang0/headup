from time import sleep
import face_recognition
import picamera
import requests
import json
import math
from requests_toolbelt import MultipartEncoder
from pygame import mixer
from datetime import datetime
import os
import logging
from logging.handlers import RotatingFileHandler

# Create a custom logger
logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

# Create file handler
f_handler = RotatingFileHandler('/home/pi/headup/headup.log', maxBytes=1024, backupCount=1)

# Create formatter and add it to handlers
formatter = logging.Formatter('%(asctime)s %(message)s')
f_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(f_handler)

def center_point(points):
    min_x = points[0][0]
    max_x = min_x
    min_y = points[0][1]
    max_y = min_y

    for x, y in points:
        if x < min_x:
            min_x = x
        if x > max_x:
            max_x = x
        if y < min_y:
            min_y = y
        if y > max_y:
            max_y = y
    return [(min_x + max_x) // 2, (min_y + max_y) // 2]

def reco_face(photo):
    '''recognize the face in the photo and return the left eys, right eys, mouth point'''
    # Load the jpg file into a numpy array
    image = face_recognition.load_image_file(photo)

    # Find all facial features in all the faces in the image
    face_landmarks_list = face_recognition.face_landmarks(image)

    if len(face_landmarks_list):
        left_eye = center_point(face_landmarks_list[0]['left_eye'])
        right_eye = center_point(face_landmarks_list[0]['right_eye'])
        mouth = center_point(face_landmarks_list[0]['bottom_lip'])
        return left_eye, right_eye, mouth
    
    return [0, 0], [0, 0], [0, 0]

def normalize(left_eye, right_eye, mouth):
    left_eye[0] = left_eye[0] - mouth[0]
    left_eye[1] = mouth[1] - left_eye[1]
    right_eye[0] = right_eye[0] - mouth[0]
    right_eye[1] = mouth[1] - right_eye[1]
    mouth[0] = 0
    mouth[1] = 0

    eye_span = math.sqrt((left_eye[0] - right_eye[0])**2 + (left_eye[1] - right_eye[1])**2 )
    if eye_span == 0:
        # Invalid eye points
        return

    ratio = 100 /eye_span
    left_eye[0], left_eye[1], right_eye[0], right_eye[1] = map(
        lambda x: int(x * ratio), [left_eye[0], left_eye[1], right_eye[0], right_eye[1]]
    )

def alarm():
    mixer.init()
    mixer.music.load('/home/pi/headup/headup.mp3')
    mixer.music.play()
    logger.debug('Head up!')

if __name__ == '__main__':
    camera = picamera.PiCamera()
    camera.resolution = (720, 480)
    camera.rotation = 180

    has_human = False
    count_no_face = 0
    count_abnormal = 0
    NORMAL_PARAM = 100

    while True:
        try:
            # Capture the image
            camera.start_preview()
            sleep(2)
            photo = 'image.jpg'
            camera.capture(photo)
            camera.stop_preview()

            # Get eyes and mouth points and normalize them
            left_eye, right_eye, mouth = reco_face(photo)
            normalize(left_eye, right_eye, mouth)
            logger.debug('face: {0}, {1}, {2}'.format(left_eye, right_eye, mouth))

            # Alarm if the head is down
            param = min(left_eye[1], right_eye[1]) - mouth[1]
            if param != 0:
                has_human = True
            else:
                count_no_face += 1
            if count_no_face > 40:
                has_human = False
                count_no_face = 0
                count_abnormal = 0
            logger.debug('param: {0}'.format(param))

            if has_human and param < NORMAL_PARAM:
                count_abnormal += 1
            if count_abnormal > 5:
                alarm()
                count_abnormal = 0

            logger.debug('has_human: {0}'.format(has_human))
            logger.debug('count_no_face: {0}'.format(count_no_face))
            logger.debug('count_abnormal: {0}'.format(count_abnormal))
        except Exception as e:
            logger.exception(e)
