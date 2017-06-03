import os
from fractions import Fraction

import flickrapi
import pyexiv2
import requests


API_KEY = os.getenv('FLICKR_API_KEY')
API_SECRET = os.getenv('FLICKR_API_SECRET')
USER_ID = os.getenv('FLICKR_USER_ID')


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


def process_photos(photos):
    for photo in photos:
        print()

        title = photo['title']
        print('Title: {}'.format(photo['title']))

        description = photo['description']['_content']
        if description:
            print('Description: {}'.format(description))

        tags = photo['tags'].split()
        if tags:
            print('Tags: {}'.format(tags))

        lat = float(photo['latitude'])
        lng = float(photo['longitude'])
        if lat or lng:
            print('Location: {}, {}'.format(lat, lng))

        if photo['media'] == 'video':
            photo_info = flickr.photos.getSizes(photo_id=photo['id'], format='parsed-json')
            sizes = photo_info['sizes']['size']
            hd = [sz['source'] for sz in sizes if sz['label'] == 'HD MP4']
            if not hd:
                print('hd not found')
                break
            else:
                hd_url = hd[0]
                requests.get(hd[0])
                print('HD video URL: {}'.format(hd[0]))
                filename = '{}.mp4'.format(photo['id'])
                path = download_file(hd_url, filename)

        else:
            original_url = photo['url_o']
            print('Original size URL: {}'.format(original_url))
            filename = '{}.jpg'.format(photo['id'])

            path = download_file(original_url, filename)

            metadata = pyexiv2.ImageMetadata(path)
            metadata.read()
            metadata['Iptc.Application2.Keywords'] = tags
            metadata['Xmp.dc.title'] = title
            metadata['Xmp.dc.description'] = description
            metadata['Exif.Image.ImageDescription'] = description
            if lat or lng:
                metadata['Exif.GPSInfo.GPSLatitude'] = abs_geo_coord(lat)
                metadata['Exif.GPSInfo.GPSLatitudeRef'] = 'N' if lat > 0 else 'S'
                metadata['Exif.GPSInfo.GPSLongitude'] = abs_geo_coord(lng)
                metadata['Exif.GPSInfo.GPSLongitudeRef'] = 'E' if lng > 0 else 'W'
            metadata.write()


# TODO:
# save the (combined) json as a metadata record, with as much info as possible
# process further pages
# fetch sets, comments, other stuff.
# apply video metadata if possible (less important if we just store the json)


flickr = flickrapi.FlickrAPI(API_KEY, API_SECRET)

data = flickr.people.getPhotos(
    user_id=USER_ID,
    per_page=50,
    format='parsed-json',
    extras='description,date_taken,tags,url_o,geo,media',
)

photos = data['photos']['photo']
process_photos(photos)
