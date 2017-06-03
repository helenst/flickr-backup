# flickr-backup

Back up flickr photos, with metadata. I've been using flickr for years and have over 5K photos in there. I have them all on disk somewhere but have
also put a lot of care into tagging / describing them on flickr, especially as Flickr's not what it once was

It pages through the API and downloads each file, setting Exif / IPTC metadata fields on photo files for title, description, tags and geolocation.

Also writes a json file listing all media (useful as it contains more than is written to the photo metadata (and also, none is written to video files).

Not particularly sophisticated, could use a bit more error handling / recovery.

If you want to use this you'll need to [create a Flickr app](https://www.flickr.com/services/apps/create/) of your own to get an API key and secret.

Requires python 3.


## Install

```
$ pip install -r requirements.txt
```

## Configure
```
export FLICKR_API_KEY='<your-api-key>'
export FLICKR_API_SECRET='<your-api-secret>'
export FLICKR_USERNAME='<your-flickr-username>'
```


## Run

```
$ python backup.py
```
