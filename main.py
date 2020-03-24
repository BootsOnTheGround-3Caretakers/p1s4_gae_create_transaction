from __future__ import absolute_import
from __future__ import unicode_literals

import sys

from six import integer_types
from six import text_type as unicode

if len(integer_types) == 1:
    long = integer_types[0]
import flask
from google.cloud import ndb

import secret
from webapp_class_wrapper import wrap_webapp_class

sys.path.insert(0, 'includes')

from datavalidation import DataValidation
from GCP_return_codes import FunctionReturnCodes as RC
from p1_global_settings import GlobalSettings
from p1_services import Services, TaskArguments
from task_queue_functions import CreateTransactionFunctions as CTF

ndb_client = ndb.Client()


def ndb_wsgi_middleware(wsgi_app):
    def middleware(environ, start_response):
        with ndb_client.context():
            return wsgi_app(environ, start_response)

    return middleware


app = flask.Flask(__name__)
app.wsgi_app = ndb_wsgi_middleware(app.wsgi_app)


class CommonPostHandler(DataValidation):
    def options(self):
        self.response.headers[str('Access-Control-Allow-Headers')] = str(
            'Cache-Control, Pragma, Origin, Authorization, Content-Type, X-Requested-With')
        self.response.headers[str('Access-Control-Allow-Methods')] = str('POST')

    def post(self, *args, **kwargs):
        debug_data = []
        task_id = 'create-transaction:CommonPostHandler:post'

        self.response.headers[str('Access-Control-Allow-Headers')] = str(
            'Cache-Control, Pragma, Origin, Authorization, Content-Type, X-Requested-With')
        self.response.headers[str('Access-Control-Allow-Methods')] = str('POST')

        call_result = self.process_request(*args, **kwargs)
        debug_data.append(call_result)
        if call_result['success'] != RC.success:
            params = {}
            for key in self.request.arguments():
                params[key] = self.request.get(key, None)

        self.create_response(call_result)

    def create_response(self, call_result):
        if call_result['success'] == RC.success:
            self.create_success_response(call_result)
        else:
            self.create_error_response(call_result)

    def create_success_response(self, call_result):
        self.response.set_status(204)

    def create_error_response(self, call_result):
        if call_result['success'] == RC.failed_retry:
            self.response.set_status(500)
        elif call_result['success'] == RC.input_validation_failed:
            self.response.set_status(400)
        elif call_result['success'] == RC.ACL_check_failed:
            self.response.set_status(401)

        self.response.out.write(call_result['return_msg'])


@app.route(Services.create_transaction.create_external_transaction.url, methods=["OPTIONS", "POST"])
@wrap_webapp_class(Services.create_transaction.create_external_transaction.name)
class CreateExternalTransaction(CommonPostHandler):
    def process_request(self):
        task_id = 'create-transaction:CreateExternalTransaction:process_request'
        debug_data = []
        return_msg = "CreateExternalTransaction:__createExternalTransaction "
        user_uid = "1"

        # input validation
        api_key = unicode(self.request.get(TaskArguments.s4t1_api_key, ""))
        task_sequence = unicode(self.request.get(TaskArguments.s4t1_task_sequence_list, ""))

        call_result = self.checkValues([
            [api_key, True, unicode, "len>1", "len<151"],
            [task_sequence, True, unicode, "len>1"],
        ])
        debug_data.append(call_result)
        if call_result['success'] != RC.success:
            return_msg += "input validation failed"
            return {'success': RC.input_validation_failed, 'return_msg': return_msg, 'debug_data': debug_data}
        # </end> input validation

        try:
            correct_api_key = secret.get_s4t1_api_key()
        except Exception as exc:
            return_msg += str(exc)
            return {'success': False, 'return_msg': return_msg, 'debug_data': debug_data}

        if api_key != correct_api_key:
            return_msg += "Invalid API key"
            return {'success': RC.ACL_check_failed, 'return_msg': return_msg, 'debug_data': debug_data}

        create_transaction = CTF()
        call_result = create_transaction.createTransaction(
            GlobalSettings.project_id, user_uid, task_id, task_sequence
        )
        debug_data.append(call_result)
        if call_result['success'] != RC.success:
            return_msg += "creating transaction failed"
            return {'success': call_result['success'], 'return_msg': return_msg, 'debug_data': debug_data}

        return {'success': RC.success, 'return_msg': return_msg, 'debug_data': debug_data}


if __name__ == "__main__":
    app.run(debug=True)
