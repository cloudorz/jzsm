# coding: utf-8

from pymongo import Connection
from pymongo.objectid import ObjectId
from gevent.wsgi import WSGIServer
from flask import Flask, redirect, url_for, render_template, jsonify, \
        request, flash, abort, session

from tornado import httpclient

from helper import get_city, get_city_by_ip


# config db
db = Connection('localhost', 27017).jzsou

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

CATES = {
        'banjia': {'no': 1, 'logo': 'move', 'label': 'banjia', 'name': u'搬家'},
        'jiadianweixiu': {'no': 2, 'logo': 'fix', 'label': 'jiadianweixiu', 'name': u'家电维修'},
        'kongtiaoyiji': {'no': 3, 'logo': 'fan', 'label': 'kongtiaoyiji', 'name': u'空调移机'},
        'guandaoshutong': {'no': 4, 'logo': 'pipe', 'label': 'guandaoshutong', 'name': u'管道疏通'},
        'kaisuo': {'no': 5, 'logo': 'unlock', 'label': 'kaisuo', 'name': u'开锁'},
        'yuesao': {'no': 6, 'logo': 'baby', 'label': 'yuesao', 'name': u'月嫂'},
        'zhongdiangong': {'no': 7, 'logo': 'clean', 'label': 'zhongdiangong', 'name': u'钟点工'},
        'xiudiannao': {'no': 8, 'logo': 'pc', 'label': 'xiudiannao', 'name': u'修电脑'},
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
        if not city_dict:
            city = get_city_by_ip()
            city_dict = get_city(city)
            session['curcity'] = city_dict
    else:
        city_dict = get_city(city)
        session['curcity'] = city_dict

    order_cates = sorted(CATES.values(), lambda e1, e2: e1['no'] - e2['no'])

    return render_template('home_list.html',
            work=city_dict['label'] in CITIES,
            cates=order_cates,
            city=city_dict)


@app.route('/getcity/<latlon>')
@app.route('/getcity/')
def set_city(latlon=None):
    if latlon:
        try:
            city_label = http_client.fetch('http://l.n2u.in/city/%s' % latlon)
        except httpclient.HTTPError, e:
            city_label = 'hangzhou'
    else:
        city_label = get_city_by_ip()

    return jsonify(get_city(city_label))


@app.route('/entry/<cate>/')
@app.route('/entry/<q>/s')
def entry_list(cate=None, q=None):

    city = session.get('curcity', CITIES['hangzhou'])
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
            entries=entries,
            city=city,
            q=q,
            cate=cate and CATES[cate],
            data_url=url)


@app.route('/s/')
def search():

    city = session.get('curcity', CITIES['hangzhou'])
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
    city = session.get('curcity', CITIES['hangzhou'])
    ipcity = get_city_by_ip()
    if ipcity not in CITIES:
        ipcity_dict = get_city(ipcity)
    else:
        ipcity_dict = CITIES[ipcity]

    order_cities = sorted(CITIES.values(), lambda e1, e2: e1['no'] - e2['no'])

    return render_template('city.html',
            cur_city=ipcity_dict,
            city=city,
            cities=order_cities,
            )


@app.route('/entry/<eid>/detail')
def detail(eid):
    back_url = request.args.get('back')
    entry = db.Entry.find_one({'_id': ObjectId(eid)})
    if not entry: abort(404)

    return render_template('detail.html',
            back=back_url,
            e=entry)


# helpers

if __name__ == "__main__":
    http_server = WSGIServer(('127.0.0.1', 8300), app)
    http_server.serve_forever()
