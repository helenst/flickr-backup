import json
import os
from fractions import Fraction
from itertools import count

import flickrapi
import pyexiv2
import requests


API_KEY = os.getenv('FLICKR_API_KEY')
API_SECRET = os.getenv('FLICKR_API_SECRET')
USER_ID = os.getenv('FLICKR_USER_ID')

PHOTOS_PER_PAGE = 10


def decdeg2dms(dd):
    """convert decimal degrees to (d, m, s)"""
    mnt, sec = divmod(dd * 3600, 60)
    deg, mnt = divmod(mnt, 60)
    return deg, mnt, sec


def abs_geo_coord(decimal_degrees):
    return [
        Fraction(int(field), 1)
        for field in decdeg2dms(abs(decimal_degrees))
    ]


def download_file(url, filename):
    path = os.path.join('downloads', filename)
    print("Downloading {} to {}".format(url, path))
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(path, 'wb') as f:
            for chunk in r:
                f.write(chunk)

    return path


class Photo:
    def __init__(self, data):
        self._data = data

    @property
    def title(self):
        return self._data['title']

    @property
    def description(self):
        return self._data['description']['_content']

    @property
    def tags(self):
        return self._data['tags'].split()

    @property
    def latitude(self):
        return float(self._data['latitude'])

    @property
    def longitude(self):
        return float(self._data['longitude'])

    @property
    def photo_id(self):
        return self._data['id']

    @property
    def original_url(self):
        return self._data['url_o']

    @property
    def is_video(self):
        return self._data['media'] == 'video'

    def process_video(self):
        photo_info = flickr.photos.getSizes(
            photo_id=self.photo_id, format='parsed-json'
        )
        sizes = photo_info['sizes']['size']
        hd = [sz['source'] for sz in sizes if sz['label'] == 'HD MP4']
        if hd:
            hd_url = hd[0]
            requests.get(hd[0])
            print('HD video URL: {}'.format(hd[0]))
            filename = '{}.mp4'.format(self.photo_id)
            download_file(hd_url, filename)
        else:
            print('hd not found')

    def process_photo(self):
        print('Original size URL: {}'.format(self.original_url))
        filename = '{}.jpg'.format(self.photo_id)

        path = download_file(self.original_url, filename)

        metadata = pyexiv2.ImageMetadata(path)
        metadata.read()
        metadata['Iptc.Application2.Keywords'] = self.tags
        metadata['Xmp.dc.title'] = self.title
        metadata['Xmp.dc.description'] = self.description
        metadata['Exif.Image.ImageDescription'] = self.description
        if self.latitude or self.longitude:
            metadata['Exif.GPSInfo.GPSLatitude'] = abs_geo_coord(self.latitude)
            metadata['Exif.GPSInfo.GPSLatitudeRef'] = 'N' if self.latitude > 0 else 'S'
            metadata['Exif.GPSInfo.GPSLongitude'] = abs_geo_coord(self.longitude)
            metadata['Exif.GPSInfo.GPSLongitudeRef'] = 'E' if self.longitude > 0 else 'W'
        metadata.write()

    def process(self):
        if self.is_video:
            self.process_video()
        else:
            self.process_photo()


# TODO:
# save the (combined) json as a metadata record, with as much info as possible
# fetch sets, comments, other stuff.
# apply video metadata if possible (less important if we just store the json)


flickr = flickrapi.FlickrAPI(API_KEY, API_SECRET)
metadata = []

for page in count(1):
    print('fetching page {}'.format(page))
    data = flickr.people.getPhotos(
        user_id=USER_ID,
        per_page=PHOTOS_PER_PAGE,
        page=page,
        format='parsed-json',
        extras='description,date_taken,tags,url_o,geo,media',
    )

    photos = data['photos']['photo']
    for photo in photos:
        Photo(photo).process()

    metadata.append(photos)

    if data['photos']['page'] == data['photos']['pages']:
        break

    if page == 2:
        break

print('Writing metadata')
with open('downloads/metadata.json', 'w') as fp:
    json.dump(metadata, fp)
