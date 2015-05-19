#!/usr/bin/env python
# coding=utf8

import json
import os
import re
import threading
import time
from unicodedata import normalize

import docker
from flask import Flask, render_template, session, g, redirect
from flask.ext.bootstrap import Bootstrap

import psutil
import requests

from flask.ext.openid import OpenID
import sqlite3dbm

import sys # SJONES
import subprocess # SJONES
os.environ['HOME'] = '/tmp' # hack for vos import
from vos import vos # ECHAPIN

# set to enable debug messages EC
DEBUG = False

app = Flask(__name__)
app.secret_key = "arglebargle"
oid = OpenID(app, os.path.join(os.path.dirname(__file__), 'openid_store'))

app.config['BOOTSTRAP_USE_MINIFIED'] = True
app.config['BOOTSTRAP_USE_CDN'] = True
app.config['BOOTSTRAP_FONTAWESOME'] = True
app.config['SECRET_KEY'] = 'devkey'

CONTAINER_STORAGE = "/usr/local/etc/jiffylab/webapp/containers.json"
SERVICES_HOST = '127.0.0.1'
# SJ comment BASE_IMAGE = 'ytproject/yt-devel'
# SJ comment BASE_IMAGE_TAG = 'jiffylab'
#BASE_IMAGE = 'public-notebook'         # SJ
#BASE_IMAGE_TAG = 'latest'              # SJ
#BASE_IMAGE = 'timeout-public-notebook'  # SJ
#BASE_IMAGE_TAG = '1.0'                  # SJ
#BASE_IMAGE = 'nugrid-notebook'           # SJ
#BASE_IMAGE_TAG = 'base'                  # SJ
BASE_IMAGE = 'swjones/nugrid-notebook'           # SJ
BASE_IMAGE_TAG = 'latest'                  # SJ


# or can use available for vm
initial_memory_budget = psutil.virtual_memory().free

# how much memory should each container be limited to, in bytes.
CONTAINER_MEM_LIMIT = 1024 * 1024 * 1024
# how much memory must remain in order for a new container to start?
MEM_MIN = CONTAINER_MEM_LIMIT + 1024 * 1024 * 1024

print >> sys.stderr, "Memory budget: %i CONTAINER_MEM_LIMIT: %i MEM_MIN: %i" % (initial_memory_budget, CONTAINER_MEM_LIMIT, MEM_MIN)

app.config.from_object(__name__)
app.config.from_envvar('FLASKAPP_SETTINGS', silent=True)

Bootstrap(app)

docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.6',
                              timeout=10)

lock = threading.Lock()


class ContainerException(Exception):

    """
    There was some problem generating or launching a docker container
    for the user
    """
    pass


_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')


def slugify(text, delim=u'-'):
    """Generates a slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))


def get_image(image_name=BASE_IMAGE, image_tag=BASE_IMAGE_TAG):
    # TODO catch ConnectionError - requests.exceptions.ConnectionError
    for image in docker_client.images():
        if image['Repository'] == image_name and image['Tag'] == image_tag:
            return image
    raise ContainerException("No image found")
    return None


def lookup_container(name):
    # TODO should this be reset at startup?
    container_store = app.config['CONTAINER_STORAGE']
    if not os.path.exists(container_store):
        with lock:
            json.dump({}, open(container_store, 'wb'))
        return None
    containers = json.load(open(container_store, 'rb'))
    try:
        return containers[name]
    except KeyError:
        return None


def check_memory():
    """
    Check that we have enough memory "budget" to use for this container

    Note this is hard because while each container may not be using its full
    memory limit amount, you have to consider it like a check written to your
    account, you never know when it may be cashed.
    """
    # the overbook factor says that each container is unlikely to be using its
    # full memory limit, and so this is a guestimate of how much you can
    # overbook your memory
    overbook_factor = .8
    remaining_budget = initial_memory_budget - \
        len(docker_client.containers()) * CONTAINER_MEM_LIMIT * overbook_factor
    if remaining_budget < MEM_MIN:
        raise ContainerException(
            "Sorry, not enough free memory to start your container"
        )


def remember_container(name, containerid):
    container_store = app.config['CONTAINER_STORAGE']
    with lock:
        if not os.path.exists(container_store):
            containers = {}
        else:
            containers = json.load(open(container_store, 'rb'))
        containers[name] = containerid
        json.dump(containers, open(container_store, 'wb'))


def forget_container(name):
    container_store = app.config['CONTAINER_STORAGE']
    with lock:
        if not os.path.exists(container_store):
            return False
        else:
            containers = json.load(open(container_store, 'rb'))
        try:
            del(containers[name])
            json.dump(containers, open(container_store, 'wb'))
        except KeyError:
            return False
        return True


def add_portmap(cont):
    if cont['Ports']:
        # a bit of a crazy comprehension to turn:
        # Ports': u'49166->8888, 49167->22'
        # into a useful dict {8888: 49166, 22: 49167}
        cont['portmap'] = dict(
            [(p['PrivatePort'], p['PublicPort']) for p in cont['Ports']])

        # wait until services are up before returning container
        # TODO this could probably be factored better when next
        # service added
        # this should be done via ajax in the browser
        # this will loop and kill the server if it stalls on docker
        ipy_wait = shellinabox_wait = True
        while ipy_wait: # SJ comment: or shellinabox_wait:
#SJ            if ipy_wait:
            try:
                requests.head("http://{host}:{port}".format(
                    host=app.config['SERVICES_HOST'],
                    port=cont['portmap'][8888]))
                ipy_wait = False
            except requests.exceptions.ConnectionError:
                pass

#SJ            if shellinabox_wait:
#SJ                try:
#SJ                    requests.head("http://{host}:{port}".format(
#SJ                        host=app.config['SERVICES_HOST'],
#SJ                        port=cont['portmap'][4200]))
#SJ                    shellinabox_wait = False
#SJ                except requests.exceptions.ConnectionError:
#SJ                    pass
            time.sleep(.2)
            if DEBUG:
                print >> sys.stderr, 'waiting', app.config['SERVICES_HOST']
        return cont


def get_container(cont_id, all=False):
    # TODO catch ConnectionError
    for cont in docker_client.containers(all=all):
        if cont_id in cont['Id']:
            return cont
    return None


def get_or_make_container(email,vospace_token='',username=''): # SJ added vospace_token and username
    # TODO catch ConnectionError
    name = slugify(unicode(email)).lower()
    container_id = lookup_container(name)
    if not container_id:
        image = get_image()
        # SJ: Here is where the docker container is created. These
        # arguments are equivalent to the command line options for
        # launching docker containers with bash.
        cont = docker_client.create_container(
            image['Id'],
            None,
            hostname="{user}box".format(user=name.split('-')[0]),
            ports=[8888, 4200],
            volumes=['/home/nugrid/CADC/NuGrid']#, # SJ declare mount points
#            mem_limit=CONTAINER_MEM_LIMIT
        )

        remember_container(name, cont['Id'])
        container_id = cont['Id']

    container = get_container(container_id, all=True)

    if not container:
        # we may have had the container cleared out
        forget_container(name)
        print >> sys.stderr, 'recurse'
        # recurse
        # TODO DANGER- could have a over-recursion guard?
        return get_or_make_container(email)

    if "Up" not in container['Status']:
        # if the container is not currently running, restart it
        check_memory()
        docker_client.start(container_id, publish_all_ports=True,
            binds={"/mnt/CADC/NuGrid/data":"/home/nugrid/CADC/NuGrid" # SJ
                })                                                       # SJ
        # refresh status
        container = get_container(container_id)

# SJ adding vospace_token to authenticated containers:
    if vospace_token is not '':
        # write the token to a file and move the file
        # inside the container:
        f=open('/usr/local/etc/jiffylab/webapp/token','w')
        f.write(vospace_token)
        f.close()
        os.system('cat /usr/local/etc/jiffylab/webapp/token | docker exec -i ' + \
                  container_id + \
                  ' bash -c "/bin/cat > /home/nugrid/.token" ')
        # remove the intermediate file
        os.system('rm /usr/local/etc/jiffylab/webapp/token')

        # checking if user has NuGrid VOspace user dir:
        users_with_dirs = subprocess.check_output('vls vos:nugrid/nb-users --token="'+\
                                            vospace_token+'"', shell=True).split('\n')
        if username not in users_with_dirs:
            # then you'd BETTER make a directory, if you know what's good for you...
            os.system('vmkdir vos:nugrid/nb-users/'+username+' --token="'+vospace_token+'"')
            os.system('vmkdir vos:nugrid/nb-users/'+username+'/notebooks --token="'+vospace_token+'"')

# end SJ

    container = add_portmap(container)
    return container

# @app.route('/', methods=['GET', 'POST'])


@app.route('/')
def index():
    try:
        container = None
        print >> sys.stderr, g.user
        if g.user:
            # return "hi user %(id)d (email %(email)s). <a
            # href='/logout'>logout</a>" %(g.user)
            container = get_or_make_container(g.user)
        return render_template('index.html',
                               container=container,
                               servicehost=app.config['SERVICES_HOST'],
                               )
    except ContainerException as e:
        session.pop('openid', None)
        return render_template('error.html', error=e)


def open_db():
    g.db = getattr(g, 'db', None) or sqlite3dbm.sshelve.open(
        "database.sqlite3")


def get_user():
    open_db()
    return g.db.get('oid-' + session.get('openid', ''))


@app.before_request
def set_user_if_logged_in():
    open_db()  # just to be explicit ...
    g.user = get_user()


@app.route("/login")
@oid.loginhandler
def login():
    if g.user is not None:
        return redirect(oid.get_next_url())
    else:
        return oid.try_login("https://www.google.com/accounts/o8/id",
                             ask_for=['email', 'fullname', 'nickname'])


@oid.after_login
def new_user(resp):
    session['openid'] = resp.identity_url
    if get_user() is None:
        user_id = g.db.get('user-count', 0)
        g.db['user-count'] = user_id + 1
        g.db['oid-' + session['openid']] = {
            'id': user_id,
            'email': resp.email,
            'fullname': resp.fullname,
            'nickname': resp.nickname}
    return redirect(oid.get_next_url())


@app.route('/logout')
def logout():
    session.pop('openid', None)
    return redirect(oid.get_next_url())


if '__main__' == __name__:
    # Put the whole thing in a try/except. If we fail we set bad exit
    # status which the CGI script can pick up
    try:
        if len(sys.argv) not in [2,3]:
            raise Exception("Arguments are: [user id] [OPTIONAL: VOS token]")
        print >> sys.stderr, sys.argv

        session_uuid = sys.argv[1]
        if (len(sys.argv) == 3) and (sys.argv[2] != ''):
            # --- Authenticated session launcher here --------------------------
            # Obtain CANFAR user name from the token and validate it by
            # trying a 'vls'-like operation on the top node of the subtree
            # of VOSpace for which the token is scoped
            vospace_token = sys.argv[2]            
            username,scope = re.match('^userid=(.*?)&.*?scope=(.*?)&.*$',vospace_token).groups()

            client = vos.Client(vospace_token=vospace_token)
            infoList = client.getInfoList(scope)
        else:
            # --- Anonymous session launcher here -----------------------------
            username = session_uuid
            vospace_token = ''
        print >> sys.stderr, "Try to launch session for user '%s' token '%s'" % (username, vospace_token) 

        container = get_or_make_container(username,vospace_token,username) # SJ added vospace_token and username
        
        # SJ making sure authenticated user has directory on VOSpace:
        if vospace_token is not '':
            pass

        # Standard ENV varible for CGI scripts
        if 'HTTP_HOST' not in os.environ:
            raise Exception('HTTP_HOST not set in environment.')

        # Full URL to session
        session_url = 'http://%s:%s' % (os.environ['HTTP_HOST'].rstrip('/'),container['portmap'][8888])
        print >> sys.stderr, session_url
        print session_url

        if DEBUG:
            print >> sys.stderr, 'All container ports:'
            print >> sys.stderr, container['Ports']

        sys.exit(0)
    except Exception as e:
        # print any exceptions to stderr to pick up in web server log
        print >> sys.stderr, e
	sys.exit(1)  
