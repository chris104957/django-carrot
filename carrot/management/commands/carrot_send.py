import json
import pprint
from django.core.management.base import BaseCommand, CommandError, CommandParser
from carrot.utilities import publish_message


class Command(BaseCommand):
    help = 'Queues a job for execution'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('job_name', type=str)
        parser.add_argument('job_args', type=str, nargs='+')

    def handle(self, *args, **options) -> None:
        job_name = options['job_name']
        job_args = options['job_args']

        if job_args:
            publish_message(job_name, *job_args)
        else:
            publish_message(job_name)
