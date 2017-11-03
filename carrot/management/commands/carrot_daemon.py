from django.core.management.base import BaseCommand
import sys
import os
import signal
import time
import subprocess
import argparse


class PidExists(Exception):
    pass


class MissingPid(Exception):
    pass


class Command(BaseCommand):
    """
    The daemon process for controlling the :class:`carrot.management.commands.carrot` service
    """
    pid_file = None
    options = None

    def delete_pid(self):
        """
        Deletes the pid file, if it exists
        """
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)

    def stop(self, hard_stop=False):
        """
        Attempts to stop the process. Performs the following actions:

        1. Asserts that the pidfile exists, or raises a :class:`MissingPid` exception
        2. Runs :function:`os.kill` on a loop until an :class:`OSError` is raised.
        3. Deletes the pidfile once the process if no longer running

        If *hard_stop* is used, the process will not wait for the consumers to finish running their current tasks

        :param bool hard_stop: if True, sends a sigkill instead of a sigterm to the consumers

        """
        assert self.pid, MissingPid('PIDFILE does not exist. The process may not be running')

        _signal = signal.SIGKILL if hard_stop else signal.SIGTERM

        while True:
            try:
                os.kill(self.pid, _signal)
                time.sleep(0.1)
            except OSError:
                break

        self.stdout.write(self.style.SUCCESS('Process has been stopped'))

        self.delete_pid()

    def add_arguments(self, parser):
        """
        This Command inherits the same arguments as :class:`carrot.management.commands.carrot.Command`, with the
        addition of one positional argument: **mode**

        :param mode:  Must be "start", "stop", "restart" or "status"
        :type mode: str

        """
        parser.add_argument('mode')
        parser.add_argument("-l", "--logfile", type=str, help='The path to the log file',
                            default='/var/log/carrot.log')
        parser.add_argument("-p", "--pidfile", type=str, help='The path to the pid file',
                            default='/var/run/carrot.pid')
        parser.add_argument('--no-scheduler', dest='run_scheduler', action='store_false', default=False,
                            help='Do not start scheduled tasks (only runs consumer sets)')
        parser.add_argument('--hard', dest='force', action='store_true', default=False,
                            help='Force stop the consumer (can only be used with stop|restart modes). USE WITH CAUTION')
        parser.set_defaults(run_scheduler=True)
        parser.set_defaults(testmode=False)

        parser.add_argument('--consumer-class', type=str, help='The consumer class to use',
                            default='carrot.objects.Consumer')
        parser.add_argument('--loglevel', type=str, default='DEBUG', help='The logging level. Must be one of DEBUG, '
                                                                          'INFO, WARNING, ERROR, CRITICAL')
        parser.add_argument('--testmode', dest='testmode', action='store_true', default=False,
                            help='Run in test mode. Prevents the command from running as a service. Should only be '
                                 'used when running Carrot\'s tests')
    @property
    def pid(self):
        """
        Opens and reads the file stored at `self.pidfile`, and returns the content as an integer. If the pidfile doesn't
        exist, then None is returned.

        :rtype: int

        """
        try:
            with open(self.pid_file, 'r') as pf:
                return int(pf.read().strip())
        except IOError:
            pass

    def write_pid(self, pid):
        """
        Writes the pid to the pidfile
        """
        with open(self.pid_file, 'w') as f:
            f.write(str(pid) + '\n')

    def start(self, **options):
        """
        Starts the carrot service as a subprocess and records the pid
        """
        if self.pid:
            raise PidExists('Process already running!')

        self.options = options
        options = ['python3', 'manage.py', 'carrot', '--verbosity', str(options.get('verbosity', 2)),
                   '--logfile', self.options['logfile'], '--loglevel', self.options['loglevel'],]

        if not self.options['run_scheduler']:
            options.append('--no-scheduler')

        if self.options['consumer_class'] != 'carrot.objects.Consumer':
            options.append('--consumer-class')
            options.append(self.options['consumer_class'])

        proc = subprocess.Popen(options, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

        self.write_pid(proc.pid)

    def handle(self, *args, **options):
        """
        The main handler. Initiates :class:`CarrotService`, then handles it based on the options supplied

        :param options: handled by *argparse*
        """
        mode = options.pop('mode')
        hard_stop = options.pop('force', False)

        if hard_stop:
            if mode not in ['stop', 'restart']:
                raise argparse.ArgumentError('force', 'This option is only valid for stop|restart modes')

        self.pid_file = options.pop('pidfile')

        if mode not in ['start', 'stop', 'restart', 'status']:
            raise argparse.ArgumentError('mode', 'Must be start, stop, restart or status')

        if mode == 'start':
            self.stdout.write('Attempting to start the process')
            self.start(**options)
            self.stdout.write(self.style.SUCCESS('Process started successfully with pid: %s' % self.pid))

        elif mode == 'stop':
            self.stdout.write('Attempting to stop the process. Please wait...')
            self.stop(hard_stop)

        elif mode == 'restart':
            try:
                self.stdout.write('Attempting to stop the process. Please wait...')
                self.stop(hard_stop)
            except MissingPid:
                self.stdout.write(self.style.WARNING('Unable to stop the process because it isn\'t running'))

            self.stdout.write('Attempting to start the process')
            self.start(**options)
            self.stdout.write(self.style.SUCCESS('Process restarted successfully'))

        elif mode == 'status':
            if self.pid:
                self.stdout.write(self.style.SUCCESS('Service is running. PID: %i' % self.pid))
            else:
                self.stdout.write(self.style.ERROR('Service is NOT running'))

        sys.exit()
