from io import StringIO
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
preference_section = 'superuser'
default_on = True

def init(app, settings):
    app.jinja_env.add_extension(AdvancedFiltersProcessor)
    app.jinja_env.add_extension(AssetIncluderProcessor)
    app.jinja_env.add_extension(SimpleMainIdProcessor)
    app.jinja_env.filters['simple_main_id'] = SimpleMainIdProcessor.postprocess

    return True

class AdvancedFiltersProcessor(Extension):
    def __init__(self, environment):
        super().__init__(environment)

    def preprocess(self, source, name, filename=None):
        try:
            tree = etree.parse(StringIO(source), etree.XMLParser(encoding='ISO-8859-1', ns_clean=True, recover=True))

            if etree.tostring(tree).decode('ISO-8859-1') != source:
                if name == 'simple/simple_search.html':
                    print("AdvancedFiltersProcessor error", source, etree.tostring(tree).decode('ISO-8859-1'))
                return source
        except Exception as e:
            return source

        form = tree.find("/form[@id='search']")

        if form is None:
            return source

        print("AdvancedFiltersProcessor form", form)

        for filter_element in self.find_filter_elements(form):
            form.remove(filter_element)

        return etree.tostring(tree).decode('ISO-8859-1')

    def parse(self, parser):
        if parser.stream.current.value != 'simple_search_filters':
            return super().parse(parser)

        lineno = next(parser.stream).lineno
        template = parser.parse_expression()

        tree = etree.fromstring(self.environment.get_template(template))

        filter_elements = etree.fromstring(
            self.find_filter_elements(tree)
        ).decode('ISO-8859-1')

        simple_filters = nodes.Const(f'{filter_elements}', lineno=lineno)

        parser.stream.skip(1)

        return nodes.CallBlock(simple_filters, [], [], []).set_lineno(lineno)

    def find_filter_elements(self, tree):
        return tree.find(
            ".//input[starts-with(@name, 'category_') or @name='language' or @name='time_range' or @name='safesearch']"
        )

class AssetIncluderProcessor(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        self.pwd = os.path.dirname(os.path.abspath(__file__))

    def preprocess(self, source, name, filename=None):
        try:
            tree = etree.parse(StringIO(source), etree.XMLParser(encoding='ISO-8859-1', ns_clean=True, recover=True))

            if etree.tostring(tree) != source:
                if name == 'simple/base.html':
                    print("AssetIncluderProcessor error", source, etree.tostring(tree).decode('ISO-8859-1'))
                return source
        except Exception as e:
            return source

        body = tree.find("//body")
        head = tree.find("//head")

        print("AssetIncluderProcessor", body, head)

        if head:
            print("AssetIncluderProcessor head", head)

            head_string = etree.tostring(head)
            link_tags = ''

            for root, dirs, files in os.walk(os.path.join(self.pwd, 'assets', 'css')):
                for file in files:
                    css = self.encode_asset(file)
                    link_tags += f'\n<link rel="stylesheet" href="{css}" type="text/css" />'

            head_string = re.sub(r"{% block styles %}.*{% endblock %}", lambda match: f"{match.group(0)}{link_tags}", head_string, flags=re.DOTALL)
            
            head.getparent().replace(head, etree.fromstring(head_string))

        if body:
            print("AssetIncluderProcessor body", body)

            script_tags = ''

            for root, dirs, files in os.walk(os.path.join(self.pwd, 'assets', 'js')):
                for file in files:
                    js = self.encode_asset(file)
                    script_tags += f'\n<script src="{js}"></script>'

            body.append(etree.fromstring(script_tags))

        output = etree.tostring(tree).decode('ISO-8859-1')
        print("AssetIncluderProcessor output", output)

        return output

    def encode_asset(self, path):
        mime, encoding = mimetypes.guess_type(path)

        with open(path, 'rb') as file:
            data = base64.b64encode(file.read()).decode('ISO-8859-1')

        return f'data:{mime};base64,{data}'

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
