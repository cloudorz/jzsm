# coding: utf-8

import json
import pygeoip

from flask import request

# loading data

data_f = open('city_dict.txt', 'rb')
data = data_f.read()

city_dict = json.loads(data)

data_f.close()

# consists
gic = pygeoip.GeoIP('/data/backup/GeoLiteCity.dat', pygeoip.MEMORY_CACHE)

def get_city(label):
    if label in city_dict:
        city = city_dict[label]
    else:
        city = city_dict['hangzhou']
    return city

def get_city_by_ip():
    ip = request.headers['X-Real-IP']
    city = 'hangzhou'
    if ip:
        record = gic.record_by_addr(ip)
        if record:
            city_ = record.get('city', None)
            if city_ and city_ in CITIES:
                city = city_.lower()
    return city
