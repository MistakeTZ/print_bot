# UpdateDate：2021/01/27

import sys
import os
from urllib import request, parse, error
from http import HTTPStatus
import base64
import json
from config import get_env
import logging

host = ""
body = None
subject_id = ""
access_token = ""


def authentication():
    global host, body, subject_id, access_token

    host = get_env("HOST")       # You will receive it when the license is issued.
    ACCEPT = 'application/json;charset=utf-8'

    AUTH_URI = 'https://' + host + '/api/1/printing/oauth2/auth/token?subject=printer'
    CLIENT_ID = get_env("CLIENT_ID")
    SECRET = get_env("CLIENT_SECRET")
    DEVICE = get_env("EMAIL")

    auth = base64.b64encode((CLIENT_ID + ':' + SECRET).encode()).decode()

    query_param = {
        'grant_type': 'password',
        'username': DEVICE,
        'password': ''
    }
    query_string = parse.urlencode(query_param)

    headers = {
        'Authorization': 'Basic ' + auth,
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
    }

    req, res, body, err_str = '', '', '', ''
    try:
        req = request.Request(AUTH_URI, data=query_string.encode('utf-8'), headers=headers, method='POST')
        with request.urlopen(req) as res:
            body = res.read()
    except error.HTTPError as err:
        err_str = str(err.code) + ':' + err.reason + ':' + str(err.read())
    except error.URLError as err:
        err_str = err.reason

    logging.info('Authentication')
    if res == '':
        logging.warning(err_str)
    else:
        logging.info("Success authentication")

    if err_str != '' or res.status != HTTPStatus.OK:
        return False

    subject_id = json.loads(body).get('subject_id')
    access_token = json.loads(body).get('access_token')


def create_print_job():
    global body

    job_uri = 'https://' + host + '/api/1/printing/printers/' + subject_id + '/jobs'

    data_param = {
        'job_name': 'SampleJob1',
        'print_mode': 'document'
    }
    data = json.dumps(data_param)

    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json;charset=utf-8'
    }

    req, res, body, err_str = '', '', '', ''
    try:
        req = request.Request(job_uri, data=data.encode('utf-8'), headers=headers, method='POST')
        with request.urlopen(req) as res:
            body = res.read()
    except error.HTTPError as err:
        err_str = str(err.code) + ':' + err.reason + ':' + str(err.read())
    except error.URLError as err:
        err_str = err.reason

    logging.info('Create print job')
    if res == '':
        logging.warning(err_str)
    else:
        logging.info("Print job created")

    if err_str != '' or res.status != HTTPStatus.CREATED:
        return False

    job_id = json.loads(body).get('id')
    return job_id


def upload_file(file_path):
    global body
    
    base_uri = json.loads(body).get('upload_uri')

    _, ext = os.path.splitext(file_path)
    file_name = '1' + ext
    upload_uri = base_uri + '&File=' + file_name

    headers = {
        'Content-Length': str(os.path.getsize(file_path)),
        'Content-Type': 'application/octet-stream'
    }

    req, res, body, err_str = '', '', '', ''
    try:
        with open(file_path, 'rb') as f:
            req = request.Request(upload_uri, data=f, headers=headers, method='POST')
            with request.urlopen(req) as res:
                body = res.read()
    except error.HTTPError as err:
        err_str = str(err.code) + ':' + err.reason + ':' + str(err.read())
    except error.URLError as err:
        err_str = err.reason

    logging.info('Upload print file')
    if res == '':
        logging.warning(err_str)
    else:
        logging.info("File uploaded")

    if err_str != '' or res.status != HTTPStatus.OK:
        return False


def execute_print(job_id):
    global body

    print_uri = 'https://' + host + '/api/1/printing/printers/' + subject_id + '/jobs/' + job_id + '/print'
    data=''

    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json; charset=utf-8'
    }

    req, res, body, err_str = '', '', '', ''
    try:
        req = request.Request(print_uri, data=data.encode('utf-8'), headers=headers, method='POST')
        with request.urlopen(req) as res:
            body = res.read()
    except error.HTTPError as err:
        err_str = str(err.code) + ':' + err.reason + ':' + str(err.read())
    except error.URLError as err:
        err_str = err.reason

    logging.info('Execute print')
    if res == '':
        logging.warning(err_str)
    else:
        logging.info("Print executed")
