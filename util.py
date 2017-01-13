import requests 
import tempfile
import shutil

async def get_image(url):
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            out_name = next(tempfile._get_candidate_names()) + '.png'
            with open(out_name, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
            return out_name
        raise ValueError