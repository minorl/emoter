from pyparsing import CaselessLiteral, StringEnd, Optional, Word, alphanums
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
from pathlib import Path

class FaceReplaceBot(SlackBot):
    def __init__(self, slack=None):
        self.name = 'Replace Faces'
        self.expr = (CaselessLiteral('facereplace') +
                     symbols.flag_with_arg('image', symbols.link) + 
                     Optional(Word(alphanums).setResultsName('name')) +
                     StringEnd()
                    )
        self.doc = ('Replace faces in a provided image with a specified face, or something better. Note: image size cannot exceed 4MB.\n'
                   '\tfacereplace --image <imagelink> [facename]')
        self.MAX_FACES = 20

        self.upload_name = 'Upload Face'
        self.upload_expr = (CaselessLiteral('faceupload') + 
                     symbols.flag_with_arg('name', symbols.alphanum_word) +
                     symbols.flag_with_arg('image', symbols.link) +
                     StringEnd()
                     )
        self.upload_doc = ('Upload face to be used in face replacement. Note: Use transparent images of a single face. ' 
                           '\n\tfaceupload --name <face name> --image <imagelink>')

        self.delete_name = 'Remove Face'
        self.delete_expr = (CaselessLiteral('faceremove') + 
                     symbols.flag_with_arg('name', symbols.alphanum_word) +
                     StringEnd()
                     )
        self.delete_doc = ('Remove face used in face replacement.' 
                           '\n\tfaceremove --name <face name> ')

        self.list_name = 'List Faces'
        self.list_expr = (CaselessLiteral('facelist') + StringEnd())
        self.list_doc = ('List faces available for use in face replacement.' 
                           '\n\tfacelist')

        self.FACE_DIR = 'faces/' #TODO: Put this in config
        self.DEFAULT_FACE = 'nick'

    @register(name='name', expr='expr', doc='doc')
    async def command_facereplace(self, user, in_channel, parsed):
        face_replacement = parsed.get('name')
        if not face_replacement:
            face_replacement = self.DEFAULT_FACE
        image_file = Path.cwd() / Path(self.FACE_DIR) / (face_replacement + '.png')
        data_file = Path.cwd() / Path(self.FACE_DIR) / (face_replacement + '.json')
        if not (image_file.exists() and data_file.exists()):  #Validate that face exists
            return MessageCommand(channel=in_channel, user=user, text='Face {} not found.'.format(face_replacement))
        try:
            img_url = parsed['image'][1:-1]
            image_file = await get_image(img_url)
        except ValueError:
            return MessageCommand(channel=in_channel, user=user, text='Image {} not found.'.format(img_url))
        
        filename = next(tempfile._get_candidate_names()) + '.png'

        with open(image_file, 'rb') as image:
            try:
                faces = await detect_face(image, self.MAX_FACES)
            except errors.HttpError as e:
                print(e._get_reason)
                return MessageCommand(channel=in_channel, user=user, text='Failed API call. Image may be too large.')
            
            # Reset the file pointer, so we can read the file again
            image.seek(0)

            if faces:
                replace_faces(image, faces, filename, face_replacement)
            else:
                return MessageCommand(channel=in_channel, user=user, text='No faces found.')

        os.remove(image_file)
        return UploadCommand(channel=in_channel, user=user, file_name=filename, delete=True)

    @register(name='upload_name', expr='upload_expr', doc='upload_doc')
    async def command_uploadface(self, user, in_channel, parsed):
        facename = parsed['name']
        
        #Check if this name is used
        if (os.path.isfile(self.FACE_DIR + facename+'.png') or os.path.isfile(self.FACE_DIR + facename+'.json')): 
            return MessageCommand(channel=in_channel, user=user, text='Face named {} already exists.'.format(facename))

        try:
            img_url = parsed['image'][1:-1]
            image_file = await get_image(img_url)
        except ValueError:
            return MessageCommand(channel=in_channel, user=user, text='Image {} not found.'.format(img_url))

        #Check file conforms (transparency)        
        with Image.open(image_file) as img:
            if not img.mode == "RGBA":
                os.remove(image_file)
                return MessageCommand(channel=in_channel, user=user, text='Image not transparent png. Please provide a transparent image.'.format(img_url))

        with open(image_file, 'rb') as image:
            try:
                faces = await detect_face(image, self.MAX_FACES)
            except errors.HttpError as e:
                print(e._get_reason)
                return MessageCommand(channel=in_channel, user=user, text='Failed API call. Image may be too large.')
            
        if len(faces) == 1:
            #Save face json file
            with open(self.FACE_DIR + facename + '.json', 'w') as facefile:
                json.dump(faces, facefile)
            os.rename(image_file, self.FACE_DIR + facename + '.png')

        else:
            return MessageCommand(channel=in_channel, user=user, 
                    text='Found {} faces, please provide an image with exactly one.'.format(len(faces)))
        
        return MessageCommand(channel=in_channel, user=user, text='Face {} successfully created.'.format(facename))

    @register(name='delete_name', expr='delete_expr', doc='delete_doc', admin=True)
    async def command_deleteface(self, user, in_channel, parsed):
        facename = parsed['name']
        if facename == self.DEFAULT_FACE:
            return MessageCommand(channel=in_channel, user=user, text='Cannot remove {}: default face.'.format(facename))
        facenamedir = self.FACE_DIR + facename
        if os.path.isfile(facenamedir+'.png'): 
            os.remove(facenamedir+'.png')
        if os.path.isfile(facenamedir+'.json'): 
            os.remove(facenamedir+'.json')
        return MessageCommand(channel=in_channel, user=user, text='Face {} removed.'.format(facename))

    @register(name='list_name', expr='list_expr', doc='list_doc')
    async def command_listfaces(self, user, in_channel, parsed):
        facepath = Path.cwd() / Path(self.FACE_DIR)
        faces = set([f.stem for f in Path(facepath).glob('*.json')]).intersection([f.stem for f in Path(facepath).glob("*.png")])
        return MessageCommand(channel=in_channel, user=user, text='Faces available for use with facereplace:\n{}'.format('\n'.join(faces)))

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

    return response['responses'][0]['faceAnnotations'] if 'faceAnnotations' in response['responses'][0] else []

def replace_faces(image, faces, output_filename, face_replacement):
    """Replace the faces.

    Args:
      image: a file containing the image with the faces.
      faces: a list of faces found in the file. This should be in the format
          returned by the Vision API.
      output_filename: the name of the image file to be created, where the
          faces have polygons drawn around them.
    """

    #Get replacement face, resize face based on fdbounding box, paste face (centered?)
    #bounding box appears to always be a square, parallel to x and y axis

    with open('faces/{}.json'.format(face_replacement)) as f:
        faceData = json.load(f)
    faceVerts = faceData[0]['fdBoundingPoly']['vertices']
    #top left corner
    faceCorner = (min(v.get('x', 0) for v in faceVerts), min(v.get('y', 0) for v in faceVerts))
    faceCoords = get_bbox_height_width(faceVerts)

    with open('faces/{}.png'.format(face_replacement), 'rb') as img:
        newFace = Image.open(img)

        im = Image.open(image).convert(mode='RGBA')

        for face in faces:
            vertices = face['fdBoundingPoly']['vertices']

            (fw, fh) = get_bbox_height_width(vertices)
            widthRatio = fw/float(faceCoords[0])
            heightRatio = fh/float(faceCoords[1])

            #get resized face, same bounding box as target face
            rface = newFace.resize((int(newFace.width*widthRatio), int(newFace.height*heightRatio)))
            #line up top left corners
            newCorner = (int(faceCorner[0]*widthRatio), int(faceCorner[1]*heightRatio))
            cFaceCorner = (min(v.get('x', 0) for v in vertices), min(v.get('y', 0) for v in vertices))

            im.paste(rface, (cFaceCorner[0]-newCorner[0], cFaceCorner[1]-newCorner[1]), rface)

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
