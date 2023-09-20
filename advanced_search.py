from jinja2 import nodes
from jinja2.ext import Extension
from lxml import etree
from pathlib import Path
import base64
import mimetypes
import os
import re

name = 'Advanced search filters'
description = 'Include advanced search filters on the homepage.'
preference_section = 'ui'
default_on = False

def init(app, settings):
    app.jinja_env.add_extension(AdvancedFiltersProcessor)
    app.jinja_env.add_extension(AssetIncluderProcessor)
    app.jinja_env.add_extension(SimpleMainIdProcessor)
    app.jinja_env.filters['simple_main_id'] = SimpleMainIdProcessor.postprocess

    return True

class AdvancedFiltersProcessor(Extension):
    def __init__(self, environment):
        super().__init__(environment)

    def find_filter_elements(self, tree):
        return tree.find(
            ".//input[starts-with(@name, 'category_') or @name='language' or @name='time_range' or @name='safesearch']"
        )

    def preprocess(self, source, name, filename=None):
        tree = etree.fromstring(source)
        form = tree.find("/form[@id='search']")

        if not form:
            return source

        for filter_element in self.find_filter_elements(form):
            form.remove(filter_element)

        return etree.tostring(tree)

    def parse(self, parser):
        if parser.stream.current.value != 'simple_search_filters':
            return super().parse(parser)

        lineno = next(parser.stream).lineno

        parser.stream.skip(1)

        tree = etree.fromstring(self.environment.get_template('simple/simple_search.html'))

        filter_elements = etree.fromstring(
            self.find_filter_elements(tree)
        )

        simple_filters = nodes.Const(f'{filter_elements}', lineno=lineno)

        return nodes.CallBlock(simple_filters, [], [], []).set_lineno(lineno)

class AssetIncluderProcessor(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        self.pwd = os.path.dirname(os.path.abspath(__file__))

    def encode_asset(self, path):
        mime, encoding = mimetypes.guess_type(path)

        with open(path, 'rb') as file:
            data = base64.b64encode(file.read()).decode('utf-8')

        return f'data:{mime};base64,{data}'

    def preprocess(self, source, name, filename=None):
        tree = etree.fromstring(source)
        body = tree.find("//body")
        head = tree.find("//head")

        if head:
            head_string = etree.tostring(head)
            link_tags = ''

            for root, dirs, files in os.walk(os.path.join(self.pwd, 'assets', 'css')):
                for file in files:
                    css = self.encode_asset(file)
                    link_tags += f'\n<link rel="stylesheet" href="{css}" type="text/css" />'

            head_string = re.sub(r"{% block styles %}.*{% endblock %}", lambda match: f"{match.group(0)}{link_tags}", head_string, flags=re.DOTALL)
            
            head.getparent().replace(head, etree.fromstring(head_string))

        if body:
            script_tags = ''

            for root, dirs, files in os.walk(os.path.join(self.pwd, 'assets', 'js')):
                for file in files:
                    js = self.encode_asset(file)
                    script_tags += f'\n<script src="{js}"></script>'

            body.append(etree.fromstring(script_tags))

        return etree.tostring(tree)

class SimpleMainIdProcessor(Extension):
    def __init__(self, environment):
        super().__init__(environment)

    def preprocess(self, source, name, filename=None):
        if re.match(r'^/[^/]+/index\.html$', name):
            return re.sub(r'replace\("simple/", ""\)\|replace\(".html", ""\)', lambda match: 'simple_main_id', source)

        return source

    @staticmethod
    def postprocess(value):
        return re.sub(r'^[^/]+/(.*?)\.html$', lambda match: match.group(1), value)
