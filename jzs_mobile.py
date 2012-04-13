# coding: utf-8

import re

from pymongo import Connection, ASCENDING, DESCENDING
from pymongo.objectid import ObjectId
from gevent.wsgi import WSGIServer
from flask import Flask, redirect, url_for, render_template, jsonify, \
        request, flash, abort, session

from tornado import httpclient

from helper import get_city, get_city_by_ip


# config db
db = Connection('localhost', 27017).jzsou

# client
http_client = httpclient.HTTPClient()

cellphone = re.compile(r'^(1(([35]\d)|(47)|[8][0126789]))\d{8}$')

# config app
app = Flask(__name__)
app.config.from_pyfile('config.cfg')

CITIES = {
        'hangzhou': {'no': 1, 'label': 'hangzhou', 'name': u'杭州'},
        'shanghai': {'no': 2, 'label': 'shanghai', 'name': u'上海'},
        'nanjing': {'no': 3, 'label': 'nanjing', 'name': u'南京'},
        'beijing': {'no': 4, 'label': 'beijing', 'name': u'北京'},
        'shenzhen': {'no': 5, 'label': 'shenzhen', 'name': u'深圳'},
        'guangzhou': {'no': 6, 'label': 'guangzhou', 'name': u'广州'},
        }


@app.errorhandler(404)
def page_not_found(error):
    return render_template("errors/404.html", error=error)

@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html", error=error)


# request handlers
@app.route('/')
@app.route('/<city>/')
def home_list(city=None):
    if not city:
        city_dict = session.get('curcity', None)
    else:
        city_dict = get_city(city)
        session['curcity'] = city_dict

    cates = db.Cate.find({}).sort('no', ASCENDING)

    return render_template('home_list.html',
            cates=cates,
            city=city_dict)


@app.route('/setcity/<latlon>')
@app.route('/setcity/')
def setcity(latlon=None):
    if latlon:
        try:
            city_label = http_client.fetch('http://l.n2u.in/city/%s' % latlon)
        except httpclient.HTTPError, e:
            city_label = 'hangzhou'
    else:
        city_label = get_city_by_ip()

    city_dict = get_city(city_label)
    session['curcity'] = city_dict

    return jsonify(city_dict)


@app.route('/getcity/<latlon>')
@app.route('/getcity/')
def getcity(latlon=None):
    if latlon:
        try:
            city_label = http_client.fetch('http://l.n2u.in/city/%s' % latlon)
        except httpclient.HTTPError, e:
            city_label = 'hangzhou'
    else:
        city_label = get_city_by_ip()

    city_dict = get_city(city_label)

    return jsonify(city_dict)


@app.route('/entry/<cate>/')
@app.route('/entry/<q>/s')
def entry_list(cate=None, q=None):

    city = session.get('curcity', get_city('hangzhou'))
    query_dict = {
            'city_label': city['label'],
            'status': 'show',
            }

    args = {
            '_id': 1,
            'title': 1,
            'address': 1,
            }

    pos = request.args.get('pos', None)
    if pos:
        lat, lon = pos.split(',')
        query_dict['_location'] = {
                '$maxDistance': 0.091,
                '$near': [float(lon), float(lat)]
                }

    st = int(request.args.get('st', 1))

    # process functions
    if cate:
        query_dict['tags'] = cate

    if q:
        rqs = [e.lower() for e in re.split('\s+', q) if e]
        regex = re.compile(r'%s' % '|'.join(rqs), re.IGNORECASE)
        query_dict['$or'] = [{'title': regex}, {'brief': regex},
                {'desc': regex}, {'tags': {'$in': rqs}}] 

    cur_entry = db.Entry.find(query_dict, args)

    num = cur_entry.count()
    entries = list(cur_entry.skip(st).limit(20))

    for e in entries:
        e['pk'] = str(e['_id'])
        del e['_id']

    # what's next
    url = None
    if st + 20 < num:
        if q:
            condition = 'key:%s' % q
        else:
            condition = 'tag:%s' % cate

        if pos:
            url = url_for('search', st=st+20, q=condition, pos=pos)
        else:
            url = url_for('search', st=st+20, q=condition)

    return render_template('entry_list.html',
            valid_city=db.City.find_one({'label': city['label'], 'block': False}),
            entries=entries,
            city=city,
            q=q,
            cate=db.Cate.find_one({'label': cate}),
            data_url=url)


@app.route('/s/')
def search():

    city = session.get('curcity', get_city('hangzhou'))
    query_dict = {
            'city_label': city['label'],
            'status': 'show',
            }
    args = {
            '_id': 1,
            'title': 1,
            'address': 1,
            }

    pos = request.args.get('pos', None)
    if pos:
        lat, lon = pos.split(',')
        query_dict['_location'] = {
                '$maxDistance': 0.091,
                '$near': [float(lon), float(lat)]
                }

    condition = request.args.get('q')
    if ':' in condition:
        field, value = condition.split(':')
    else:
        abort(400)

    st = int(request.args.get('st', 1))

    # process functions
    def do_tag(tag):
        query_dict['tags'] = tag
        return db.Entry.find(query_dict, args)

    def do_key(data):
        rqs = [e.lower() for e in re.split('\s+', data) if e]
        regex = re.compile(r'%s' % '|'.join(rqs), re.IGNORECASE)
        query_dict['$or'] = [{'title': regex}, {'brief': regex},
                {'desc': regex}, {'tags': {'$in': rqs}}] 
        return db.Entry.find(query_dict, args)

    handle_q = {
            'tag': do_tag, 
            'key': do_key,
            }

    if field in handle_q:
        cur_entry = handle_q[field](value)
        num = cur_entry.count()
        entries = list(cur_entry.skip(st).limit(20))

        for e in entries:
            e['pk'] = str(e['_id'])
            del e['_id']

        # what's next
        if st + 20 < num:
            if pos:
                next = url_for('search', q=condition, st=st+20, pos=pos)
            else:
                next = url_for('search', q=condition, st=st+20)
        else:
            next = None

        return render_template('macros/_listcell.html',
                entries=entries,
                next=next)
    else:
        abort(400)


@app.route('/city/')
def change_city():

    cities = db.City.find({'block': False}).sort('no', ASCENDING)

    return render_template('city.html',
            cities=cities,
            )


@app.route('/entry/<eid>/detail')
def detail(eid):
    back_url = request.args.get('back')
    entry = db.Entry.find_one({'_id': ObjectId(eid)})

    phones = entry['contracts']
    # get phone
    tel = None
    for e in phones:
        if not cellphone.match(e):
            tel = e
            break

    if not tel:
        if len(phones) >= 3:
            tel = phones[1]
        else:
            tel = phones[0]

    if not entry: abort(404)

    return render_template('detail.html',
            back=back_url,
            tel=tel,
            is_cell=bool(cellphone.match(tel)),
            e=entry)


# helpers

if __name__ == "__main__":
    http_server = WSGIServer(('127.0.0.1', 8300), app)
    http_server.serve_forever()
