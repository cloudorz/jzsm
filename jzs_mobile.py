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


@app.errorhandler(404)
def page_not_found(error):
    return render_template("errors/404.html", error=error)

@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html", error=error)


# request handlers
@app.route('/')
@app.route('/<city>')
def home_list(city=None):
    return render_template('home_list.html',
            city=city)


@app.route('/entry/<city>/<cate>')
@app.route('/entry/<city>/<q>')
def entry_list(city, cate=None, q=None):
    return render_template('entry_list.html',
            city=city,
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


@app.route('/city/')
def change_city(name=None):
    return render_template('city.html')


@app.route('/entry/<eid>')
def detail(eid):
    entry = db.Entry.find_one({'_id': eid})
    if not entry: abort(404)

    return render_template('detail.html', entry=entry)


if __name__ == "__main__":
    http_server = WSGIServer(('127.0.0.1', 8300), app)
    http_server.serve_forever()
