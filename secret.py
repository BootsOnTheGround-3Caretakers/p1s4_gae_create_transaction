from __future__ import unicode_literals

import os

import six

if six.PY2:
    from google.appengine.api import app_identity

    project_id = unicode(app_identity.get_application_id())
else:
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')

import google
from google.cloud import secretmanager_v1beta1 as secretmanager


def get_secret_value(secret_id, default=None, raise_exception=True):
    try:
        version_id = 1

        client = secretmanager.SecretManagerServiceClient()

        name = client.secret_version_path(project_id, secret_id, version_id)
        response = client.access_secret_version(name)

        return response.payload.data.decode('UTF-8')
    except google.api_core.exceptions.NotFound:
        if default is None and raise_exception:
            raise

        return default


def get_s4t1_api_key():
    return get_secret_value("S4T1_API_KEY")
