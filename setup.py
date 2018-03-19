import os
from setuptools import find_packages, setup


def readme():
    with open('README.rst') as f:
        return f.read()


os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


setup(
    name='django-carrot',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    license='Apache Software License',
    description='A RabbitMQ asynchronous task queue for Django.',
    long_description=readme(),
    author='Christopher Davies',
    author_email='christopherdavies553@gmail.com',
    url='https://django-carrot.readthedocs.org',
    classifiers=[
        'Environment :: Web Environment',
        'Development Status :: 5 - Production/Stable',
        'Framework :: Django',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires=['django>=1.9', 'json2html==1.2.1', 'pika>=0.10.0', 'djangorestframework>=3.6']
)

