"""
An astronomical plugin, for providing the system with astronomical data (e.g. whether it's day or not, based on the sun's location)
"""

import re
import sys
import time
import requests
import simplejson as json
from datetime import datetime, timedelta
from plugins.base import om_expose, background_task, OMPluginBase, PluginConfigChecker

# FIXME Something seems wrong with UTC to localtime. Why using localtime at all?
# FIXME Version should be 0.5.3 or 0.6.0


def try_fun(tries, fun, *args):
    while --tries > 0:
        try:
            return fun(*args)
        except Exception as e:
            print e
            time.sleep(60)


class Astro(OMPluginBase):
    """
    An astronomical plugin, for providing the system with astronomical data (e.g. whether it's day or not, based on the sun's location)
    """

    name = 'Astro'
    version = '0.5.5'
    interfaces = [('config', '1.0')]

    config_description = [{'name': 'location',
                           'type': 'str',
                           'description': 'A location which will be passed to Google to fetch location, timezone and elevation.'},
                          {'name': 'horizon_bit',
                           'type': 'int',
                           'description': 'The bit that indicates whether it is day. -1 when not in use.'},
                          {'name': 'civil_bit',
                           'type': 'int',
                           'description': 'The bit that indicates whether it is day or civil twilight. -1 when not in use.'},
                          {'name': 'nautical_bit',
                           'type': 'int',
                           'description': 'The bit that indicates whether it is day, civil or nautical twilight. -1 when not in use.'},
                          {'name': 'astronomical_bit',
                           'type': 'int',
                           'description': 'The bit that indicates whether it is day, civil, nautical or astronomical twilight. -1 when not in use.'},
                          {'name': 'bright_bit',
                           'type': 'int',
                           'description': 'The bit that indicates the brightest part of the day. -1 when not in use.'},
                          {'name': 'bright_offset',
                           'type': 'int',
                           'description': 'The offset (in minutes) after sunrise and before sunset on which the bright_bit should be set.'},
                          {'name': 'group_action',
                           'type': 'int',
                           'description': 'The ID of a Group Action to be called when another zone is entered. -1 when not in use.'}]

    default_config = {'location': 'Brussels,Belgium',
                      'horizon_bit': -1,
                      'civil_bit': -1,
                      'nautical_bit': -1,
                      'astronomical_bit': -1,
                      'bright_bit': -1,
                      'bright_offset': 60,
                      'group_action': -1}

    def __init__(self, webinterface, logger):
        super(Astro, self).__init__(webinterface, logger)
        self.logger('Starting Astro plugin...')

        self._config = self.read_config(Astro.default_config)
        self._config_checker = PluginConfigChecker(Astro.config_description)

        pytz_egg = '/opt/openmotics/python/plugins/Astro/pytz-2017.2-py2.7.egg'
        if pytz_egg not in sys.path:
            sys.path.insert(0, pytz_egg)

        self._read_config()

        self.logger("Started Astro plugin")

    def _read_config(self):
        for bit in ['bright_bit', 'horizon_bit', 'civil_bit', 'nautical_bit', 'astronomical_bit']:
            try:
                value = int(self._config.get(bit, Astro.default_config[bit]))
            except ValueError:
                value = Astro.default_config[bit]
            setattr(self, '_{0}'.format(bit), value)
        try:
            self._bright_offset = int(self._config.get('bright_offset', Astro.default_config['bright_offset']))
        except ValueError:
            self._bright_offset = Astro.default_config['bright_offset']
        try:
            self._group_action = int(self._config.get('group_action', Astro.default_config['group_action']))
        except ValueError:
            self._group_action = Astro.default_config['group_action']

        self._enabled = False
        if self._config['location'] != '':
            address = self._config['location']
            self._location = self._translate_coordinates(address)
            if (self._location):
                self._enabled = True
            else:
                self.logger('Could not translate {0} to coordinates')

        self.logger('Astro is {0}'.format('enabled' if self._enabled else 'disabled'))

    @staticmethod
    def _convert(dt_string):
        import pytz
        date = datetime.strptime(dt_string, '%Y-%m-%dT%H:%M:%S+00:00')
        date = pytz.utc.localize(date)
        if date.year == 1970:
            return None
        return date

    @staticmethod
    def _get_time_points(location, local_now):
        url = 'http://api.sunrise-sunset.org/json?lat={0}&lng={1}&date={2}&formatted=0'
        response = requests.get(url.format(location['lat'], location['lng'], local_now.strftime('%Y-%m-%d'))).json()
        return response['results']

    @staticmethod
    def _parse_coordinates(coord_str):
        m = re.match(r'(\d+\.\d+)\ +(\d+\.\d+)', coord_str)
        if not m:
            return None
        lat = m.group(1)
        lng = m.group(2)
        return {'lat': lat, 'lng': lng}

    def _translate_coordinates(self, address):
        location = Astro._parse_coordinates(address)
        if location:
            self.logger('Location provided as coordinates')
            return location

        self.logger('Location provided as address, translating to coordinates...')
        url = 'https://maps.googleapis.com/maps/api/geocode/json?address={0}'
        response = requests.get(url.format(address)).json()

        if response['status'] != 'OK':
            print response
            raise Exception('Cannot translate address to coordinates')

        return response['results'][0]['geometry']['location']

    @staticmethod
    def _add_bright(time_points, offset):
        horizon = time_points['horizon']
        if horizon is None:
            return time_points

        bright_begin = horizon['begin'] + timedelta(minutes=offset)
        bright_end = horizon['end'] - timedelta(minutes=offset)
        has_bright = bright_begin < bright_end
        time_points['bright'] = {'begin': bright_begin, 'end': bright_end} if has_bright else None

        return time_points

    @staticmethod
    def _convert_time_points(data):
        horizon_begin = Astro._convert(data['sunrise'])
        horizon_end = Astro._convert(data['sunset'])
        civil_begin = Astro._convert(data['civil_twilight_begin'])
        civil_end = Astro._convert(data['civil_twilight_end'])
        has_civil = civil_begin is not None and civil_end is not None
        nautical_begin = Astro._convert(data['nautical_twilight_begin'])
        nautical_end = Astro._convert(data['nautical_twilight_end'])
        has_nautical = nautical_begin is not None and nautical_end is not None
        astronomical_begin = Astro._convert(data['astronomical_twilight_begin'])
        astronomical_end = Astro._convert(data['astronomical_twilight_end'])
        has_astronomical = astronomical_begin is not None and astronomical_end is not None
        return {
            'horizon': {'begin': horizon_begin, 'end': horizon_end},
            'civil': {'begin': civil_begin, 'end': civil_end} if has_civil else None,
            'nautical': {'begin': nautical_begin, 'end': nautical_end} if has_nautical else None,
            'astronomical': {'begin': astronomical_begin, 'end': astronomical_end} if has_astronomical else None,
        }

    # FIXME _loop needs refactory, too complex
    def _loop(self):
        import pytz

        now = datetime.now(pytz.utc)
        local_now = datetime.now()
        local_tomorrow = datetime(local_now.year, local_now.month, local_now.day) + timedelta(days=1)

        # Try at most two times
        time_points = try_fun(2, Astro._get_time_points, self._location, local_now)

        # Use cached values (yesterday) if today is not available
        if time_points:
            self._time_points = time_points
        elif self._time_points is not None:
            self.logger('Cannot get time points, using cached values')
            time_points = self._time_points

        if not time_points:
            self.logger('Cannot get time points. Astro disabled.')
            self._enabled = False
            return

        time_points = Astro._convert_time_points(time_points)
        time_points = Astro._add_bright(time_points, self._bright_offset)
        sleep = 24 * 60 * 60
        bits = [True, True, True, True, True]  # ['bright', day, civil, nautical, astronomical]

        self.logger(time_points)

        # FIXME fallback sleep if cannot get time points

        has_sun = time_points['horizon'] is not None
        has_civil = time_points['civil'] is not None
        has_nautical = time_points['nautical'] is not None
        has_astronomical = time_points['astronomical'] is not None
        has_bright = time_points['bright'] is not None
        horizon_begin = time_points['horizon']['begin']
        horizon_end = time_points['horizon']['end']
        civil_begin = time_points['civil']['begin']
        civil_end = time_points['civil']['end']
        bright_begin = time_points['bright']['begin']
        bright_end = time_points['bright']['end']
        nautical_begin = time_points['nautical']['begin']
        nautical_end = time_points['nautical']['end']
        astronomical_begin = time_points['astronomical']['begin']
        astronomical_end = time_points['astronomical']['end']

        # Analyse data
        if not any([has_sun, has_civil, has_nautical, has_astronomical]):
            # This is an educated guess; Polar day (sun never sets) and polar night (sun never rises) can
            # happen in the polar circles. However, since we have far more "gradients" in the night part,
            # polar night (as defined here - pitch black) only happens very close to the poles. So it's
            # unlikely this plugin is used there.
            info = 'polar day'
            bits = [True, True, True, True, True]
            sleep = (local_tomorrow - local_now).total_seconds()
        else:
            if has_bright is False:
                bits[0] = False
            else:
                bits[0] = bright_begin < now < bright_end
                if bits[0] is True:
                    sleep = min(sleep, (bright_end - now).total_seconds())
                elif now < bright_begin:
                    sleep = min(sleep, (bright_begin - now).total_seconds())
            if has_sun is False:
                bits[1] = False
            else:
                bits[1] = horizon_begin < now < horizon_end
                if bits[1] is True:
                    sleep = min(sleep, (horizon_end - now).total_seconds())
                elif now < horizon_begin:
                    sleep = min(sleep, (horizon_begin - now).total_seconds())
            if has_civil is False:
                if has_sun is True:
                    bits[2] = not bits[1]
                else:
                    bits[2] = False
            else:
                bits[2] = civil_begin < now < civil_end
                if bits[2] is True:
                    sleep = min(sleep, (civil_end - now).total_seconds())
                elif now < horizon_begin:
                    sleep = min(sleep, (civil_begin - now).total_seconds())
            if has_nautical is False:
                if has_sun is True or has_civil is True:
                    bits[3] = not bits[2]
                else:
                    bits[3] = False
            else:
                bits[3] = nautical_begin < now < nautical_end
                if bits[3] is True:
                    sleep = min(sleep, (nautical_end - now).total_seconds())
                elif now < horizon_begin:
                    sleep = min(sleep, (nautical_begin - now).total_seconds())
            if has_astronomical is False:
                if has_sun is True or has_civil is True or has_nautical is True:
                    bits[4] = not bits[3]
                else:
                    bits[4] = False
            else:
                bits[4] = astronomical_begin < now < astronomical_end
                if bits[4] is True:
                    sleep = min(sleep, (astronomical_end - now).total_seconds())
                elif now < horizon_begin:
                    sleep = min(sleep, (astronomical_begin - now).total_seconds())
            sleep = min(sleep, (local_tomorrow - local_now).total_seconds())
            info = 'night'
            if bits[4] is True:
                info = 'astronimical twilight'
            if bits[3] is True:
                info = 'nautical twilight'
            if bits[2] is True:
                info = 'civil twilight'
            if bits[1] is True:
                info = 'day'
            if bits[0] is True:
                info = 'day (bright)'
        # Set bits in system
        for index, bit in {0: self._bright_bit,
                           1: self._horizon_bit,
                           2: self._civil_bit,
                           3: self._nautical_bit,
                           4: self._astronomical_bit}.iteritems():
            if bit > -1:
                result = json.loads(self.webinterface.do_basic_action(None, 237 if bits[index] else 238, bit))
                if result['success'] is False:
                    self.logger('Failed to set bit {0} to {1}'.format(bit, 1 if bits[index] else 0))
        if self._previous_bits != bits:
            if self._group_action != -1:
                result = json.loads(self.webinterface.do_basic_action(None, 2, self._group_action))
                if result['success'] is True:
                    self.logger('Group Action {0} triggered'.format(self._group_action))
                else:
                    self.logger('Failed to trigger Group Action {0}'.format(self._group_action))
            self._previous_bits = bits
        self.logger('It\'s {0}. Going to sleep for {1} seconds'.format(info, round(sleep, 1)))
        time.sleep(sleep + 5)

    @background_task
    def run(self):
        self._time_points = None
        self._previous_bits = [None, None, None, None, None]
        while True:
            if self._enabled:
                self._loop()
            else:
                time.sleep(5)

    @om_expose
    def get_config_description(self):
        return json.dumps(Astro.config_description)

    @om_expose
    def get_config(self):
        return json.dumps(self._config)

    @om_expose
    def set_config(self, config):
        config = json.loads(config)
        for key in config:
            if isinstance(config[key], basestring):
                config[key] = str(config[key])
        self._config_checker.check_config(config)
        self._config = config
        self._read_config()
        self.write_config(config)
        return json.dumps({'success': True})
