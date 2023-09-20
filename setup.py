from setuptools import setup

setup(
    author = 'SatoshiGuacamole',
    name = 'searxng-advanced-search-plugin',
    description = 'Include advanced search filters on the homepage.',
    license = 'MIT',
    install_requires = [
       'jinja2>=3',
       'lxml>=4',
    ],
    py_modules = ['advanced_search'],
)
