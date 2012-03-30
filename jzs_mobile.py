# coding: utf-8

from pymongo import Connection
from gevent.wsgi import WSGIServer
from flask import Flask, redirect, url_for, render_template, jsonify, \
        request, flash, abort


# config db
db = Connection('localhost', 27017).jzsou

# config app
app = Flask(__name__)
app.config.from_pyfile('config.cfg')

# consists
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
def home_list(city='hangzhou'):
    order_cates = sorted(CATES.values(), lambda e1, e2: e1['no'] - e2['no'])
    return render_template('home_list.html',
            cates=order_cates,
            city=CITIES[city])


@app.route('/entry/<city>/<cate>/cate')
@app.route('/entry/<city>/<q>/search')
def entry_list(city, cate=None, q=None):
    return render_template('entry_list.html',
            city=CITIES[city],
            cate=cate and CATES[cate],
            q=q)


@app.route('/<city>/s/')
def search(city):

        query_dict = {
                'city_label': city,
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

        condition = ('q')
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
            cur_entry = handle_q[field](v)
            num = cur_entry.count()
            entries = cur_entry.skip(st).limit(20)

            for e in entries_raw:
                e['id'] = str(e['_id'])
                del e['_id']

            # what's next
            if st + 20 < num:
                if pos:
                    next = url_for('search', q=condition, st=st+20, pos=pos)
                else:
                    next = url_for('search', q=condition, st=st+20)
            else:
                next = None

            return jsonify({'next': next, 'entries': entries})
        else:
            abort(400)


@app.route('/city/<cur_city>')
def change_city(cur_city):
    order_cities = sorted(CITIES.values(), lambda e1, e2: e1['no'] - e2['no'])
    return render_template('city.html',
            cities=order_cities,
            cur_city=CITIES[cur_city])


@app.route('/entry/<eid>/detail')
def detail(eid):
    entry = db.Entry.find_one({'_id': eid})
    if not entry: abort(404)

    return render_template('detail.html', entry=entry)


if __name__ == "__main__":
    http_server = WSGIServer(('127.0.0.1', 8300), app)
    http_server.serve_forever()
