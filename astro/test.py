import requests
import time


def log(msg):
    print msg


def translate_coordinates(address):
    api = 'https://maps.googleapis.com/maps/api/geocode/json?address={0}'.format(address)
    response = requests.get(api).json()

    if response['status'] != 'OK':
        raise Exception('Cannot translate address to coordinates')

    latitude = response['results'][0]['geometry']['location']['lat']
    longitude = response['results'][0]['geometry']['location']['lng']

    return latitude, longitude


def try_translate_coordinates(address, tries):
    while --tries > 0:
        try:
            return translate_coordinates(address)
        except Exception:
            time.sleep(60)


print try_translate_coordinates('Bordugo,Italy', 2)
