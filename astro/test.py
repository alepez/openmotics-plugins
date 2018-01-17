import requests
import time
import simplejson as json
from datetime import datetime, timedelta


def translate_coordinates(address):
    url = 'https://maps.googleapis.com/maps/api/geocode/json?address={0}'
    response = requests.get(url.format(address)).json()

    if response['status'] != 'OK':
        print response
        raise Exception('Cannot translate address to coordinates')

    return response['results'][0]['geometry']['location']


def convert_time_string(dt_string):
    import pytz
    date = datetime.strptime(dt_string, '%Y-%m-%dT%H:%M:%S+00:00')
    date = pytz.utc.localize(date)
    if date.year == 1970:
        return None
    return date


def get_time_points(location, time):
    url = 'http://api.sunrise-sunset.org/json?lat={0}&lng={1}&date={2}&formatted=0'
    response = requests.get(url.format(location['lat'], location['lng'], local_now.strftime('%Y-%m-%d'))).json()
    return response['results']


def convert_time_points(data):
    horizon_begin = convert_time_string(data['sunrise'])
    horizon_end = convert_time_string(data['sunset'])
    civil_begin = convert_time_string(data['civil_twilight_begin'])
    civil_end = convert_time_string(data['civil_twilight_end'])
    has_civil = civil_begin is not None and civil_end is not None
    nautical_begin = convert_time_string(data['nautical_twilight_begin'])
    nautical_end = convert_time_string(data['nautical_twilight_end'])
    has_nautical = nautical_begin is not None and nautical_end is not None
    astronomical_begin = convert_time_string(data['astronomical_twilight_begin'])
    astronomical_end = convert_time_string(data['astronomical_twilight_end'])
    has_astronomical = astronomical_begin is not None and astronomical_end is not None
    return {
        'horizon': { 'begin': horizon_begin, 'end': horizon_end },
        'civil': { 'begin': civil_begin, 'end': civil_end } if has_civil else None,
        'nautical': { 'begin': nautical_begin, 'end': nautical_end } if has_nautical else None,
        'astronomical': { 'begin': astronomical_begin, 'end': astronomical_end } if has_astronomical else None,
    }


def try_fun(tries, fun, *args):
    while --tries > 0:
        try:
            return fun(*args)
        except Exception as e:
            print e
            time.sleep(60)


def get_time_points_stub(location, time):
    return json.loads('{"sunrise":"2018-01-17T06:46:39+00:00","sunset":"2018-01-17T15:57:29+00:00","solar_noon":"2018-01-17T11:22:04+00:00","day_length":33050,"civil_twilight_begin":"2018-01-17T06:13:50+00:00","civil_twilight_end":"2018-01-17T16:30:18+00:00","nautical_twilight_begin":"2018-01-17T05:37:14+00:00","nautical_twilight_end":"2018-01-17T17:06:53+00:00","astronomical_twilight_begin":"2018-01-17T05:01:50+00:00","astronomical_twilight_end":"2018-01-17T17:42:17+00:00"}')


def translate_coordinates_stub(address):
    return { 'lat': 45.5759938, 'lng': 12.0413745 }


def add_bright(time_points, offset):
    horizon = time_points['horizon']
    if horizon is None:
        return time_points

    bright_begin = horizon['begin'] + timedelta(minutes=offset)
    bright_end = horizon['end'] - timedelta(minutes=offset)
    has_bright = bright_begin < bright_end
    time_points['bright'] = { 'begin': bright_begin, 'end': bright_end } if has_bright else None

    return time_points


address = 'Bordugo,Italy'

# location = try_fun(2, translate_coordinates, address)
location = translate_coordinates_stub(address)

local_now = datetime.now()
# time_points = try_fun(2, get_time_points, location, local_now)
time_points = get_time_points_stub(location, local_now)

converted_time_points = convert_time_points(time_points)
with_bright = add_bright(converted_time_points, 60)

for i in [ 'horizon', 'civil', 'nautical', 'astronomical', 'bright' ]:
    for j in [ 'begin', 'end' ]:
        print "{0} - {1} - {2}".format(i, j, with_bright[i][j])
