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

PHOTOS_PER_PAGE = 500

EXTRA_FIELDS = (
    'description, license, date_upload, date_taken, owner_name, '
    'icon_server, original_format, last_update, geo, tags, machine_tags, '
    'o_dims, views, media, path_alias, url_sq, url_t, url_s, url_q, url_m, '
    'url_n, url_z, url_c, url_l, url_o'
)

DOWNLOAD_DIR = 'downloads/'


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


class FlickrMedia:
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
    def is_photo(self):
        return self._data['media'] == 'photo'

    @property
    def is_video(self):
        return self._data['media'] == 'video'

    @property
    def file_path(self):
        ext = 'jpg' if self.is_photo else 'mp4'
        filename = '{}.{}'.format(self.photo_id, ext)
        return os.path.join(DOWNLOAD_DIR, filename)

    @property
    def photo_url(self):
        assert self.is_photo

        return self._data['url_o']

    @property
    def video_url(self):
        """
        Get the video url for this media item

        It's not in the metadata so has to be requested.
        """
        assert self.is_video

        photo_info = flickr.photos.getSizes(
            photo_id=self.photo_id, format='parsed-json'
        )
        sizes = photo_info['sizes']['size']
        hd = [sz['source'] for sz in sizes if sz['label'] == 'HD MP4']
        if hd:
            return hd[0]
        else:
            print('hd not found')

    def write_metadata(self):
        """
        Write metadata to the file (Must be downloaded first)
        """
        if self.is_photo:
            metadata = pyexiv2.ImageMetadata(self.file_path)
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

    def download_file(self):
        """
        Download the file to local storage
        """
        url = self.photo_url if self.is_photo else self.video_url
        to_path = self.file_path

        print("Downloading {} to {}".format(url, to_path))
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(to_path, 'wb') as f:
                for chunk in r:
                    f.write(chunk)

    def process(self):
        self.download_file()
        self.write_metadata()


# TODO:
# fetch sets, comments, other stuff.
# apply video metadata if possible (less important if we just store the json)

if __name__ == '__main__':
    flickr = flickrapi.FlickrAPI(API_KEY, API_SECRET)
    metadata = []

    for page in count(1):
        print('fetching page {}'.format(page))
        data = flickr.people.getPhotos(
            user_id=USER_ID,
            per_page=PHOTOS_PER_PAGE,
            page=page,
            format='parsed-json',
            extras=EXTRA_FIELDS,
        )

        photos = data['photos']['photo']
        for photo in photos:
            FlickrMedia(photo).process()

        metadata.extend(photos)

        if data['photos']['page'] == data['photos']['pages']:
            break

    print('Writing metadata')
    with open('downloads/metadata.json', 'w') as fp:
        json.dump(metadata, fp)
