#  -*- coding: utf-8 -*-
# encoding: utf-8

import json
import os
from time import time
import re
import requests
from base64 import b64encode

from kitty.data.report import Report
from kitty.targets.server import ServerTarget
from requests.exceptions import RequestException

from utils import set_class_logger


@set_class_logger
class FuzzerTarget(ServerTarget):
    def not_implemented(self, func_name):
        pass

    def __init__(self, name, base_url, report_dir):
        super(FuzzerTarget, self).__init__(name)
        self.base_url = base_url
        self._last_sent_request = None
        self.accepted_status_codes = list(range(200, 300)) + list(range(400, 500))
        self.report_dir = report_dir
        self.logger.info('Logger initialized')

    def error_report(self, msg, req):
        if hasattr(req, 'request'):
            self.report.add('request method', req.request.method)
            self.report.add('request body', req.request.body)
            self.report.add('response', req.text)
        else:
            for k, v in req.items():
                if isinstance(v, dict):
                    for subkey, subvalue in v.items():
                        self.report.add(subkey, b64encode(subvalue))
                else:
                    self.report.add(k, b64encode(v))
        self.report.set_status(Report.ERROR)
        self.report.error(msg)

    def save_report_to_disc(self):
        try:
            if not os.path.exists(os.path.dirname(self.report_dir)):
                try:
                    os.makedirs(os.path.dirname(self.report_dir))
                except OSError:
                    pass
            with open('{}/{}_{}.json'.format(self.report_dir, self.test_number, time()), 'wb') as report_dump_file:
                report_dump_file.write(json.dumps(self.report.to_dict(), ensure_ascii=False, encoding='utf-8'))
        except Exception as e:
            self.logger.error(
                'Failed to save report "{}" to {} because: {}'
                 .format(self.report.to_dict(), self.report_dir, e)
            )

    def transmit(self, **kwargs):
        try:
            _req_url = list()
            for url_part in self.base_url, kwargs['url']:
                self.logger.info('URL part: {}'.format(url_part))
                _req_url.append(url_part.strip('/'))
            request_url = '/'.join(_req_url)
            request_url = self.expand_path_variables(request_url, kwargs.get('path_variables'))
            request_url = self.expand_query_parameters(request_url, kwargs.get('params'))
            if kwargs.get('path_variables'):
                kwargs.pop('path_variables')
            kwargs.pop('url')
            self.logger.warn('>>> Formatted URL: {} <<<'.format(request_url))

	    if "API_FUZZER_API_KEY" in os.environ:
                headers = {'Authorization': 'api-key {}'.format(os.getenv("API_FUZZER_API_KEY", ""))}
                headers_sanitized = {'Authorization': 'api-key THIS_IS_THE_API_KEY_FROM_ENVIRONMENT'}
                if 'headers' in kwargs:
                    combinedHeaders = {key: value for (key, value) in (headers.items() + kwargs['headers'].items())}
                    combinedHeadersSanitized = {key: value for (key, value) in (headers_sanitized.items() + kwargs['headers'].items())}
                    del kwargs['headers']
                    headers = combinedHeaders
                    headers_sanitized = combinedHeadersSanitized
                self.logger.warn('Request Headers:{}, KWARGS:{}, url: {}'.format(headers_sanitized, kwargs, _req_url))
                _return = requests.request(url=request_url, headers=headers, verify=False, **kwargs)
	    else:
                self.logger.warn('Request KWARGS:{}, url: {}'.format(kwargs, _req_url))
                _return = requests.request(url=request_url, verify=False, **kwargs)

            status_code = _return.status_code
            if status_code:
                if status_code not in self.accepted_status_codes:
                    self.report.add('parsed status_code', status_code)
                    self.report.add('request method', _return.request.method)
                    self.report.add('request body', _return.request.body)
                    self.report.add('response', _return.text)
                    self.report.set_status(Report.FAILED)
                    self.report.failed('return code {} is not in the expected list'.format(status_code))
            else:
                self.error_report('Failed to parse http response code', _return.headers)
            return _return
        except (RequestException, UnicodeDecodeError) as e:  # request failure such as InvalidHeader
            self.error_report('Failed to parse http response code, exception: {}'.format(e), kwargs)

    def post_test(self, test_num):
        """Called after a test is completed, perform cleanup etc."""
        super(FuzzerTarget, self).post_test(test_num)
        if self.report.get('status') != Report.PASSED:
            self.save_report_to_disc()

    def expand_path_variables(self, url, path_parameters):
        if not isinstance(path_parameters, dict):
            self.logger.error('path_parameters: {}'.format(path_parameters))
            return url
        for path_key, path_value in path_parameters.items():
            try:
                _temporally_url_list = list()
                path_parameter = path_key.split('|')[-1]
                splitter = '({' + path_parameter + '})'
                url_list = re.split(splitter, url)
                self.logger.info('Processing: {} key: {} splitter: {} '.format(url_list, path_parameter, splitter))
                for url_part in url_list:
                    if url_part == '{' + path_parameter + '}':
                        _temporally_url_list.append(path_value.decode('unicode-escape').encode('utf8'))
                    else:
                        _temporally_url_list.append(url_part.encode())
                url = "".join(_temporally_url_list)
                self.logger.warn('url 1: {} | {}->{}'.format(url, path_parameter, path_value))
            except Exception as e:
                self.logger.warn('Failed to replace string in url: {} param: {}, exception: {}'.format(url, path_value, e))
        url = url.replace("{", "").replace("}", "")
        return url

    def expand_query_parameters(self, url, query_parameters):
        if not isinstance(query_parameters, dict):
            self.logger.error('query_parameters: {}'.format(query_parameters))
            return url
        url = url + '?'
        for param_key, param_value in query_parameters.items():
            try:
                pkey = param_key.split('|')[-1]
		url=url + pkey + '=' + param_value.decode('unicode-escape').encode('utf8') + '&'
            except Exception as e:
                self.logger.warn('Failed to replace string in url: {} param: {}, exception: {}'.format(url, path_value, e))
        return url
