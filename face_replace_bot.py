from pyparsing import CaselessLiteral, StringEnd
from slack.bot import SlackBot, register
from slack.command import MessageCommand, UploadCommand
from slack.parsing import symbols
from util import get_image
import tempfile
from googleapiclient import discovery, errors
import json
import base64
from PIL import Image
from PIL import ImageDraw
import os
import asyncio

class FaceReplaceBot(SlackBot):
    def __init__(self, slack=None):
        self.name = 'Replace Faces'
        self.expr = (CaselessLiteral('facereplace') +
                     symbols.flag_with_arg('image', symbols.link) + 
                     StringEnd()
                    )
        self.doc = ('Replace faces in a provided image with something better. Note: image size cannot exceed 4MB.\n'
                   '\tfacereplace --image <imagelink>')
        self.MAX_FACES = 20

    @register(name='name', expr='expr', doc='doc')
    async def command_facereplace(self, user, in_channel, parsed):
        try:
            img_url = parsed['image'][1:-1]
            image_file = await get_image(img_url)
        except ValueError:
            return MessageCommand(channel=None, user=user, text='Image {} not found.'.format(img_url))
        
        filename = next(tempfile._get_candidate_names()) + '.png'

        with open(image_file, 'rb') as image:
            try:
                faces = await detect_face(image, self.MAX_FACES)
            except errors.HttpError:
                return MessageCommand(channel=None, user=user, text='Failed API call. Image may be too large.')
            # Reset the file pointer, so we can read the file again
            image.seek(0)
            replace_faces(image, faces, filename)

        os.remove(image_file)
        return UploadCommand(channel=in_channel, user=user, file_name=filename, delete=True)

def get_vision_service():
    return discovery.build('vision', 'v1')


async def detect_face(face_file, max_results=4):
    """Uses the Vision API to detect faces in the given file.

    Args:
        face_file: A file-like object containing an image with faces.

    Returns:
        An array of dicts with information about the faces in the picture.
    """
    image_content = face_file.read()
    batch_request = [{
        'image': {
            'content': base64.b64encode(image_content).decode('utf-8')
            },
        'features': [{
            'type': 'FACE_DETECTION',
            'maxResults': max_results,
            }]
        }]

    service = get_vision_service()
    request = service.images().annotate(body={
        'requests': batch_request,
        })
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, request.execute)

    return response['responses'][0]['faceAnnotations']

def replace_faces(image, faces, output_filename):
    """Nick Cage the faces.

    Args:
      image: a file containing the image with the faces.
      faces: a list of faces found in the file. This should be in the format
          returned by the Vision API.
      output_filename: the name of the image file to be created, where the
          faces have polygons drawn around them.
    """

    #Get nick, resize nick based on fdbounding box, paste nick (centered?)
    #bounding box appears to always be a square, parallel to x and y axis

    with open('faces/nick.json') as f:
        nickFaceData = json.load(f)
    nickVerts = nickFaceData[0]['fdBoundingPoly']['vertices']
    #top left corner
    nickFaceCorner = (min(v.get('x', 0.0) for v in nickVerts), min(v.get('y', 0.0) for v in nickVerts))
    nickFaceCoords = get_bbox_height_width(nickVerts)

    with open('faces/nick.png', 'rb') as img:
        nick = Image.open(img)

        im = Image.open(image).convert(mode='RGBA')

        for face in faces:
            vertices = face['fdBoundingPoly']['vertices']

            (fw, fh) = get_bbox_height_width(vertices)
            widthRatio = fw/float(nickFaceCoords[0])
            heightRatio = fh/float(nickFaceCoords[1])

            #get resized nick face, same bounding box as target face
            rnick = nick.resize((int(nick.width*widthRatio), int(nick.height*heightRatio)))
            #line up top left corners
            newNickCorner = (int(nickFaceCorner[0]*widthRatio), int(nickFaceCorner[1]*heightRatio))
            faceCorner = (min(v.get('x', 0.0) for v in vertices), min(v.get('y', 0.0) for v in vertices))
            
            im.paste(rnick, (faceCorner[0]-newNickCorner[0], faceCorner[1]-newNickCorner[1]), rnick)

    im.save(output_filename)

def get_bbox_height_width(vertices):
    x0 = vertices[0].get('x', 0.0)
    y0 = vertices[0].get('y', 0.0)
    height = 0
    width = 0

    for v in vertices[1:]:
        xi = v.get('x', 0.0)
        yi = v.get('y', 0.0)

        if(x0 == xi):
            height = abs(y0-yi)
        if(y0 == yi):
            width = abs(x0-xi)

    return (width, height)
