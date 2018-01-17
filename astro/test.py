import requests
import time
from datetime import datetime, timedelta


def translate_coordinates(address):
    url = 'https://maps.googleapis.com/maps/api/geocode/json?address={0}'
    response = requests.get(url.format(address)).json()

    if response['status'] != 'OK':
        print response
        raise Exception('Cannot translate address to coordinates')

    location = response['results'][0]['geometry']['location']
    return location['lat'], location['lng']


def convert(dt_string):
    import pytz
    date = datetime.strptime(dt_string, '%Y-%m-%dT%H:%M:%S+00:00')
    date = pytz.utc.localize(date)
    if date.year == 1970:
        return None
    return date


def get_time_points(lat, lon, time):
    url = 'http://api.sunrise-sunset.org/json?lat={0}&lng={1}&date={2}&formatted=0'
    response = requests.get(url.format(lat, lon, local_now.strftime('%Y-%m-%d'))).json()
    data = response['results']
    sunrise = convert(data['sunrise'])
    sunset = convert(data['sunset'])
    civil_start = convert(data['civil_twilight_begin'])
    civil_end = convert(data['civil_twilight_end'])
    has_civil = civil_start is not None and civil_end is not None
    nautical_start = convert(data['nautical_twilight_begin'])
    nautical_end = convert(data['nautical_twilight_end'])
    has_nautical = nautical_start is not None and nautical_end is not None
    astronomical_start = convert(data['astronomical_twilight_begin'])
    astronomical_end = convert(data['astronomical_twilight_end'])
    has_astronomical = astronomical_start is not None and astronomical_end is not None
    return {
        'horizon': { 'begin': sunrise, 'end': sunset },
        'civil': { 'begin': civil_start, 'end': civil_end } if has_civil else None,
        'nautical': { 'begin': nautical_start, 'end': nautical_end } if has_nautical else None,
        'astronomical': { 'begin': astronomical_start, 'end': astronomical_end } if has_astronomical else None,
    }


def try_fun(tries, fun, *args):
    while --tries > 0:
        try:
            return fun(*args)
        except Exception:
            time.sleep(60)

# def add_bright(sunrise, sunset, offset):
#     has_sun = sunrise is not None and sunset is not None
#     if has_sun is True:
#         bright_start = sunrise + timedelta(minutes=self._bright_offset)
#         bright_end = sunset - timedelta(minutes=self._bright_offset)
#         has_bright = bright_start < bright_end
#     else:
#         has_bright = False


address = 'Bordugo,Italy'

lat, lon = try_fun(2, translate_coordinates, address)
# lat, lon = (45.5759938, 12.0413745)

local_now = datetime.now()
time_points = try_fun(2, get_time_points, lat, lon, local_now)

print time_points
