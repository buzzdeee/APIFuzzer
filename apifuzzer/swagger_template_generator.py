from base_template import BaseTemplate
from template_generator_base import TemplateGenerator
from utils import get_sample_data_by_type, get_fuzz_type_by_param_type, set_class_logger


class ParamTypes(object):
    PATH = 'path'
    QUERY = 'query'
    HEADER = 'header'
    COOKIE = 'cookie'
    BODY = 'body'
    FORM_DATA = 'formData'


@set_class_logger
class SwaggerTemplateGenerator(TemplateGenerator):

    def __init__(self, api_resources):
        self.api_resources = api_resources
        self.templates = list()
        self.logger.info('Logger initialized')
        self.parameters = {}

    def process_api_resources(self):
        self.logger.info('Start preparation')
	if "openapi" in self.api_resources.keys():
	    swagger_version = self.api_resources["openapi"]
	if "swagger" in self.api_resources.keys():
	    swagger_version = self.api_resources["swagger"]
	print "Swagger version: " + str(swagger_version)

	if 'parameters' in self.api_resources.keys():
	    self.parameters = self.api_resources['parameters']
	    print self.parameters

        for resource in self.api_resources['paths'].keys():
	    print "RESOURCE: " + resource
            normalized_url = resource.lstrip('/').replace('/', '_')
            for method in self.api_resources['paths'][resource].keys():
		if swagger_version == "2.0":
		    self.handle_v2_json(normalized_url, resource, method)
		else:
		    self.handle_v3_json(normalized_url, resource, method)

    def handle_v3_json(self, normalized_url, resource, method):
		print "METHOD: " + method
                self.logger.info('Resource: {} Method: {}'.format(resource, method))
		if 'parameters' in self.api_resources['paths'][resource][method]:
		    params = self.api_resources['paths'][resource][method]['parameters']
		    self.parse_v3_parameters(normalized_url, resource, method, params)

    def parse_v3_parameters(self, normalized_url, resource, method, parameters):
        for param in parameters:
            template_container_name = '{}|{}|{}'.format(normalized_url, method, param.get('name'))
            template = BaseTemplate(name=template_container_name)
            template.url = resource
            template.method = method.upper()
            self.logger.info('Resource: {} Method: {} Parameter: {}'.format(resource, method, param))
            fuzz_type = get_fuzz_type_by_param_type(param['schema'].get('type'))
            sample_data = get_sample_data_by_type(param['schema'].get('type'))
	    print "FUZZ TYPE: " + str(fuzz_type)
	    print "SAMPLE DATA: " + str(sample_data)
            # get parameter placement(in): path, query, header, cookie
            # get parameter type: integer, string
            # get format if present
            param_type = param.get('in')
            param_name = template_container_name
            if param_type == ParamTypes.PATH:
                template.path_variables.append(fuzz_type(name=param_name, value=sample_data))
            elif param_type == ParamTypes.HEADER:
                template.headers.append(fuzz_type(name=param_name, value=sample_data))
            elif param_type == ParamTypes.COOKIE:
                template.cookies.append(fuzz_type(name=param_name, value=sample_data))
            elif param_type == ParamTypes.QUERY:
                template.params.append(fuzz_type(name=param_name, value=sample_data))
            elif param_type in [ParamTypes.BODY, ParamTypes.FORM_DATA]:
                template.data.append(fuzz_type(name=param_name, value=sample_data))
            else:
                self.logger.error('Cant parse a definition from swagger.json: %s', param)
            self.templates.append(template)

    def handle_v2_json(self, normalized_url, resource, method):
		print "METHOD: " + method
                self.logger.info('Resource: {} Method: {}'.format(resource, method))
		if "parameters" == method:
		    params = self.api_resources['paths'][resource]['parameters']
		    self.parse_v2_parameters(normalized_url, resource, 'unknown', params)
		    print self.api_resources['paths'][resource]['parameters']
		else:
		    if 'parameters' in self.api_resources['paths'][resource][method]:
		        params = self.api_resources['paths'][resource][method]['parameters']
		        self.parse_v2_parameters(normalized_url, resource, method, params)

    def parse_v2_parameters(self, normalized_url, resource, method, parameters):
        for param in parameters:
	    if '$ref' in param.keys():
		print "OOPS"
		ref = param['$ref'].split('/')
		print ref
		param = self.parameters[ref[2]]
		print param
	    print "PARAM: " + str(param)
	    # check if we have an object description
	    if 'schema' in param.keys():
		# Well, it might be that there is a parameter called 'schema'
		# and not being an object, so only analyze 'schema' parameters
		# if they have 'properties'
		if 'properties' in param['schema'].keys():
		    self.analyze_object_schema(normalized_url, resource, method, param)
		    return
            template_container_name = '{}|{}|{}'.format(normalized_url, method, param.get('name'))
            template = BaseTemplate(name=template_container_name)
            template.url = resource
            template.method = method.upper()
            self.logger.info('Resource: {} Method: {} Parameter: {}'.format(resource, method, param))
            fuzz_type = get_fuzz_type_by_param_type(param.get('type'))
            sample_data = get_sample_data_by_type(param.get('type'))
            # get parameter placement(in): path, query, header, cookie
            # get parameter type: integer, string
            # get format if present
            param_type = param.get('in')
	    print "IN: " + param.get('in')
            param_name = template_container_name
            if param_type == ParamTypes.PATH:
                template.path_variables.append(fuzz_type(name=param_name, value=sample_data))
            elif param_type == ParamTypes.HEADER:
                template.headers.append(fuzz_type(name=param_name, value=sample_data))
            elif param_type == ParamTypes.COOKIE:
                template.cookies.append(fuzz_type(name=param_name, value=sample_data))
            elif param_type == ParamTypes.QUERY:
                template.params.append(fuzz_type(name=param_name, value=sample_data))
            elif param_type in [ParamTypes.BODY, ParamTypes.FORM_DATA]:
                template.data.append(fuzz_type(name=param_name, value=sample_data))
            else:
                self.logger.error('Cant parse a definition from swagger.json: %s', param)
            self.templates.append(template)

    def analyze_object_schema(self, normalized_url, resource, method, schema):
	print "SCHEMA: " + str(schema)
	for param in schema['schema']['properties']:
	    print "AAA: " + param
	    template_container_name = '{}|{}|{}'.format(normalized_url, method, param)
	    template = BaseTemplate(name=template_container_name)
            template.url = resource
            template.method = method.upper()
	    self.logger.info('Resource: {} Method: {} Parameter: {}'.format(resource, method, param))
	    fuzz_type = get_fuzz_type_by_param_type(schema['schema'].get('type'))
	    sample_data = get_sample_data_by_type(schema['schema'].get('type'))
	    param_type = schema.get('in')
	    print "IN: " + schema.get('in')
	    param_name = template_container_name
            if param_type == ParamTypes.PATH:
                template.path_variables.append(fuzz_type(name=param_name, value=sample_data))
            elif param_type == ParamTypes.HEADER:
                template.headers.append(fuzz_type(name=param_name, value=sample_data))
            elif param_type == ParamTypes.COOKIE:
                template.cookies.append(fuzz_type(name=param_name, value=sample_data))
            elif param_type == ParamTypes.QUERY:
                template.params.append(fuzz_type(name=param_name, value=sample_data))
            elif param_type in [ParamTypes.BODY, ParamTypes.FORM_DATA]:
                template.data.append(fuzz_type(name=param_name, value=sample_data))
            else:
                self.logger.error('Cant parse a definition from swagger.json: %s', param)
            self.templates.append(template)

    def compile_base_url(self, alternate_url):
        """
        :param alternate_url: alternate protocol and base url to be used instead of the one defined in swagger
        :type alternate_url: string
        """

        if alternate_url:
            _base_url = "/".join([
                alternate_url.strip('/'),
                self.api_resources.get('basePath', '')
            ]).strip('/')
        else:
	    if 'schemes' not in self.api_resources:
		self.logger.error('Missing info about scheme in json, use -u to provide URL to test')
		exit (1)
            if 'http' in self.api_resources['schemes']:
                _protocol = 'http'
            else:
                _protocol = self.api_resources['schemes'][0]
	    if 'host' not in self.api_resources:
		self.logger.error('Missing info about hostname in json, use -u to provide URL to test')
		exit (1)
	    if 'basePath' not in self.api_resources:
		self.logger.error('Missing info about basePath in json, use -u to provide URL to test')
		exit (1)
	    
            _base_url = '{}://{}{}'.format(
                _protocol,
                self.api_resources['host'],
                self.api_resources['basePath']
            )
        return _base_url
