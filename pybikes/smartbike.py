# -*- coding: utf-8 -*-
# Copyright (C) 2010-2012, eskerda <eskerda@gmail.com>
# Distributed under the AGPL license, see LICENSE.txt

import re
import json
from lxml import html

from .base import BikeShareSystem, BikeShareStation
from . import utils

__all__ = [
    'SmartBike', 'SmartBikeStation',
    'SmartShitty', 'SmartShittyStation'
]

LAT_LNG_RGX = 'point \= new GLatLng\((.*?)\,(.*?)\)'
ID_ADD_RGX = 'idStation\=(.*)\&addressnew\=(.*)\&s\_id\_idioma'
ID_ADD_RGX_V = 'idStation\=\"\+(.*)\+\"\&addressnew\=(.*)\+\"\&s\_id\_idioma'

parse_methods = {
    'xml': 'get_xml_stations',
    'json': 'get_json_stations',
    'json_v2': 'get_json_v2_stations'
}


class BaseSystem(BikeShareSystem):
    meta = {
        'system': 'SmartBike',
        'company': 'ClearChannel'
    }


class SmartBike(BaseSystem):
    sync = True

    def __init__(self, tag, meta, feed_url, format="json"):
        super(SmartBike, self).__init__(tag, meta)
        self.feed_url = feed_url
        if format not in parse_methods:
            raise Exception('Unsupported method %s' % format)
        self.method = parse_methods[format]

    def update(self, scraper=None):
        if scraper is None:
            scraper = utils.PyBikesScraper()

        raw_req = scraper.request(self.feed_url)
        self.stations = eval(self.method)(self, raw_req)


def get_xml_stations(self, raw):
    raise Exception("Not implemented")


def get_json_stations(self, raw):
    # Double encoded json FTWTF..
    data = json.loads(json.loads(raw)[1]['data'])
    stations = map(SmartBikeStation, data)
    return stations


def get_json_v2_stations(self, raw):
    data = json.loads(raw)
    stations = map(SmartBikeStation, data)
    return stations


class SmartBikeStation(BikeShareStation):
    def __init__(self, info):
        super(SmartBikeStation, self).__init__(0)
        try:
            self.name = info['StationName']
            self.bikes = int(info['StationAvailableBikes'])
            self.free = int(info['StationFreeSlot'])
            self.latitude = float(info['AddressGmapsLatitude'])
            self.longitude = float(info['AddressGmapsLongitude'])
            self.extra = {
                'uid': int(info['StationID']),
                'status': info['StationStatusCode'],
                'districtCode': info['DisctrictCode'],
                'NearbyStationList': map(
                    int, info['NearbyStationList'].split(',')
                )
            }
        except KeyError:
            # Either something has changed, or it's the other type of feed
            # Same data, different keys.
            self.name = info['name']
            self.bikes = int(info['bikes'])
            self.free = int(info['slots'])
            self.latitude = float(info['lat'])
            self.longitude = float(info['lon'])
            self.extra = {
                'uid': int(info['id']),
                'status': info['status'],
                'address': info['address']
            }

            if 'district' in info:
                self.extra['districtCode'] = info['district']
            elif 'districtCode' in info:
                self.extra['districtCode'] = info['districtCode']

            if info['nearbyStations'] and info['nearbyStations'] != "0":
                self.extra['NearbyStationList'] = map(
                    int, info['nearbyStations'].split(',')
                )

            if 'zip' in info and info['zip']:
                self.extra['zip'] = info['zip']

            if 'stationType' in info and \
                    info['stationType'] == 'ELECTRIC_BIKE':
                self.extra['ebikes'] = True


class SmartShitty(BaseSystem):
    """
    BikeMI decided to implement yet another way of displaying the map...
    So, I guess what we will do here is using a regular expression to get the
    info inside the $create function, and then load that as a JSON. Who the
    fuck pay this guys money, seriously?

    <script type="text/javascript">
    //<![CDATA[
    Sys.Application.add_init(function() {
        $create(Artem.Google.MarkersBehavior, {
            "markerOptions":[
                {
                    "clickable":true,
                    "icon":{
                        ...
                    },
                    "optimized":true,
                    "position":{
                        "lat":45.464683238625966,
                        "lng":9.18879747390747
                    },
                    "raiseOnDrag":true,
                    "title":"01 - Duomo",    _____ Thank you...
                    "visible":true,         /
                    "info":"<div style=\"width: 240px; height: 100px;\">
                                <span style=\"font-weight: bold;\">
                                    01 - Duomo
                                </span>
                                <br/>
                                <ul>
                                    <li>Available bicycles: 17</li>
                                    <li>Available electrical bicycles: 0</li>
                                    <li>Available slots: 7</li>
                                </ul>
                            </div>
                }, ...
            ],
            "name": "fuckeduplongstring"
        }, null, null, $get("station-map"));
    })
    """
    sync = True

    _RE_MARKERS = 'Google\.MarkersBehavior\,\ (?P<data>.*?)\,\ null'

    def __init__(self, tag, meta, feed_url):
        super(SmartShitty, self).__init__(tag, meta)
        self.feed_url = feed_url

    def update(self, scraper=None):
        if scraper is None:
            scraper = utils.PyBikesScraper()

        page = scraper.request(self.feed_url)
        markers = json.loads(
            re.search(SmartShitty._RE_MARKERS, page).group('data')
        )['markerOptions']
        self.stations = map(SmartShittyStation, markers)


class SmartShittyStation(BikeShareStation):
    def __init__(self, marker):
        super(SmartShittyStation, self).__init__()
        avail_soup = html.fromstring(marker['info'])
        availability = list(map(
            lambda x: int(x.split(':')[1]),
            avail_soup.xpath("//div/ul/li/text()")
        ))
        self.name = marker['title']
        self.latitude = marker['position']['lat']
        self.longitude = marker['position']['lng']
        self.bikes = availability[0] + availability[1]
        self.free = availability[2]
        self.extra = {}
        if availability[1] > 0:
            self.extra['has_ebikes'] = True
            self.extra['ebikes'] = availability[2]
