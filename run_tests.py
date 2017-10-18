import django, sys, os
from django.conf import settings
import argparse
from carrot.objects import VirtualHost


def runner(options):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(BASE_DIR)

    vhost = {
        'host': options.host,
        'port': options.port,
        'name': options.name,
        'username': options.username,
        'password': options.password,
        'secure': options.secure,
    }
    _vhost = VirtualHost(**vhost)

    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'local',
            }
        },
        ROOT_URLCONF='carrot.urls',
        INSTALLED_APPS=(
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.admin',
            'django.contrib.staticfiles',
            'carrot',
        ),
        CARROT={
            'default_broker': str(_vhost),
        },
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [os.path.join(BASE_DIR, 'templates')],
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.debug',
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                    ],
                    'builtins': ['carrot.templatetags.filters'],
                },
            },
        ],
        STATIC_URL='/static/',
    )
    django.setup()

    from django.test.runner import DiscoverRunner

    test_runner = DiscoverRunner(verbosity=0)

    failures = test_runner.run_tests(['carrot'])
    if failures:
        sys.exit(failures)


def main():
    parser = argparse.ArgumentParser(description='Run the Carrot test suite')
    parser.add_argument("-H", '--host', type=str, default='localhost', help='The RabbitMQ host')
    parser.add_argument("-p", '--port', type=int, default=5672, help='The port number')
    parser.add_argument("-n", '--name', type=str, default='/', help='The virtual host name')
    parser.add_argument("-U", '--username', type=str, default='guest', help='Your RabbitMQ username')
    parser.add_argument("-P", '--password', type=str, default='guest', help='Your RabbitMQ password')
    parser.set_defaults(secure=False)
    parser.add_argument('-s', '--secure', dest='secure', action='store_true', default=False,
                        help='Connect to RabbitMQ host over HTTPS')

    args = parser.parse_args()
    runner(args)

if __name__ == '__main__':
    main()