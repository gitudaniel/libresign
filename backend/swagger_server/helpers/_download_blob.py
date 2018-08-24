
import requests

def download_blob_stream(blob):
    url = blob.generate_download_url(expires=60)
    r = requests.get(url)

    return r.content
