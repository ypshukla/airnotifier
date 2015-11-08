#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2012, Dongsheng Cai
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the Dongsheng Cai nor the names of its
#      contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL DONGSHENG CAI BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging
import tornado
import os
import pymongo
from util import *
try:
    from pymongo.connection import Connection as MongoClient
except ImportError:
    from pymongo import MongoClient
from bson import *
from constants import VERSION
from tornado.options import define, options

define("apns", default=(), help="APNs address and port")
define("pemdir", default="pemdir", help="Directory to store pems")
define("passwordsalt", default="d2o0n1g2s0h3e1n1g", help="Being used to make password hash")

define("mongohost", default="localhost", help="MongoDB host name")
define("mongoport", default=27017, help="MongoDB port")
define("mongodbname", default="airnotifier", help="MongoDB database name")
define("masterdb", default="airnotifier", help="MongoDB DB to store information")
define("collectionprefix", default="obj_", help="Collection name prefix")
define("appprefix", default="", help="DB name prefix")

MONGO = MongoClient(options.mongohost, options.mongoport)
ANDB = MONGO[options.masterdb]

def bump_db_version(version):
    ANDB['options'].update_one({'name': 'version'}, {'$set': {'value': version}}, upsert=True)

def get_db_version():
    version_object = ANDB['options'].find_one({'name': 'version'})
    return version_object['value']

if __name__ == "__main__":
    curpath = os.path.dirname(os.path.realpath(__file__))
    tornado.options.parse_config_file("%s/airnotifier.conf" % curpath)
    tornado.options.parse_command_line()

    check_environment()

    # XXX: DEBUG remove line below in production
    #bump_db_version(20000000)

    version = get_db_version()
    appprefix = options.appprefix

    if version < 20140315:
        apps = ANDB['applications'].find()
        for app in apps:
            appname = app['shortname']
            appid = ObjectId(app['_id'])
            ## Repair application setting collection
            if not 'blockediplist' in app:
                app['blockediplist'] = ''
            if not 'description' in app:
                app['description'] = ''
            if not 'gcmprojectnumber' in app:
                app['gcmprojectnumber'] = ''
            if not 'gcmapikey' in app:
                app['gcmapikey'] = ''
            ANDB['applications'].replace_one({'_id': appid}, app)

            ## Adding device to token collections
            db = MONGO[appprefix + appname]
            tokens = db['tokens'].find()
            for token in tokens:
                tokenid = ObjectId(token['_id'])
                if not 'device' in token:
                    token['device'] = DEVICE_TYPE_IOS
                    result = db['tokens'].replace_one({'_id': tokenid}, token)
        bump_db_version(20140315)

    if version < 20140720:
        apps = ANDB['applications'].find()
        for app in apps:
            appname = app['shortname']
            appid = ObjectId(app['_id'])
            ## Repair application setting collection
            if not 'wnsclientid' in app:
                app['wnsclientid'] = ''
            if not 'wnsclientsecret' in app:
                app['wnsclientsecret'] = ''
            if not 'wnsaccesstoken' in app:
                app['wnsaccesstoken'] = ''
            if not 'wnstokentype' in app:
                app['wnstokentype'] = ''
            if not 'wnstokenexpiry' in app:
                app['wnstokenexpiry'] = ''
            ANDB['applications'].replace_one({'_id': appid}, app)
        bump_db_version(20140720)

    if version < 20140814:
        ## Don't store fullpath in db, only filename
        import os
        apps = ANDB['applications'].find()
        for app in apps:
            appname = app['shortname']
            appid = ObjectId(app['_id'])
            if app.has_key('certfile'):
                app['certfile'] = os.path.basename(app.get('certfile'))
            if app.has_key('keyfile'):
                app['keyfile'] = os.path.basename(app.get('keyfile'))
            if app.has_key('mpnscertificatefile'):
                app['mpnscertificatefile'] = os.path.basename(app.get('mpnscertificatefile'))
            ANDB['applications'].replace_one({'_id': appid}, app)
        bump_db_version(20140814)

    if version < 20140820:
        apps = ANDB['applications'].find()
        for app in apps:
            appname = app['shortname']
            appid = ObjectId(app['_id'])
            ## Repair application setting collection
            if not 'clickatellusername' in app:
                app['clickatellusername'] = ''
            if not 'clickatellpassword' in app:
                app['clickatellpassword'] = ''
            if not 'clickatellappid' in app:
                app['clickatellappid'] = ''
            ANDB['applications'].replace_one({'_id': appid}, app)
        bump_db_version(20140820)

    if version < 20151101:
        apps = ANDB['applications'].find()
        for app in apps:
            appname = app['shortname']
            db = MONGO[appprefix + appname]
            indexes = [("created", pymongo.DESCENDING)]
            logging.info("Adding index to %s%s['tokens'].%s" % (appprefix, appname,
                "created"))
            db['tokens'].create_index(indexes)
            logging.info("Adding index to %s%s['logs'].%s" % (appprefix, appname,
                "created"))
            db['logs'].create_index(indexes)
        bump_db_version(20151101)

    # bump to current version
    bump_db_version(VERSION)

    version = get_db_version()
    logging.info("You're using version: %d" % version)
