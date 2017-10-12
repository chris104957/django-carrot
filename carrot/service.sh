#!/bin/bash

# edit the following line items for your project
PYTHON_BINARY="/usr/local/bin/python3"
PROJECT_DIR="/path/to/django/project"

NAME=carrot_consumer
PIDFILE=/var/run/$NAME.pid

function start {
        if [ ! -f $PIDFILE ]; then
           sudo $PYTHON_BINARY $PROJECT_DIR/manage.py carrot </dev/null &>/dev/null &
           pid=$!
           echo "Daemon started succesfully with PID: $pid"
           touch $PIDFILE
           echo $pid > $PIDFILE
        else
           echo "Service already running"
        fi
}

function stop {
        if [ ! -f $PIDFILE ]; then
           echo "Process not running!"
        else
           cat $PIDFILE | while read line
           do
              sudo kill $line
              echo "Terminated process: $line"
           done
           sudo rm $PIDFILE
        fi
}

case "$1" in
  start)
        echo "Starting daemon: "$NAME
        start
        ;;
  stop)
        echo "Stopping daemon: "$NAME
        stop
        ;;
  restart)
        echo "Restarting daemon: "$NAME
        stop
        start
        ;;
  status)
        if [ ! -f $PIDFILE ]; then
          echo "Service not running"
        else
          echo "Service is running"
        fi
        ;;

  *)
        echo "Usage: "$1" {start|stop|restart}"
        exit 1
esac

exit 0

