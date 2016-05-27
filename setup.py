from setuptools import setup

setup(
    name='youtube',
    version='0.1',
    description='A wrapper to the Youtube Data API',
    author='Daniel Duong',
    license='BSD',
    py_modules=['youtube'],
    install_requires=['youtube-dl', 'google-api-python-client'],
)
