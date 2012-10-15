#!/bin/bash

SORTDB_USER=prod
SORTDB_FILE=/home/prod/brianm/bt_data.txt
SORTDB_PORT=8080
CURRENT_PID=$(ps aux | grep '/usr/local/bin/sortdb' | egrep -v grep | awk '{print $2}')

function start() {
    # we use memory lock, so we need huge memory lock limit
    sudo -u $SORTDB_USER /bin/sh -c 'ulimit -l unlimited'

    sudo -u $SORTDB_USER mkdir -p $(dirname $SORTDB_FILE)    
    if [ ! -f $SORTDB_FILE ] 
    then
        # data file does not exist, but needs to or sortdb gets upset
        sudo -u $SORTDB_USER /bin/sh -c "echo 'hello world' > $SORTDB_FILE"
    fi

    # if already running, consider this success
    if [ "" == "$CURRENT_PID" ] 
    then
        #not running yet

        sudo -u $SORTDB_USER /usr/local/bin/sortdb \
            --db-file=$SORTDB_FILE \
            --daemon \
            --port=$SORTDB_PORT
            #--memory-lock
    fi
}

function stop() {
    if [ "" == "$CURRENT_PID" ]
    then
        echo "not running"
        exit 0
    else
        kill $CURRENT_PID
        CURRENT_PID=""
    fi
}

function status {
    if [ ! "" == "$CURRENT_PID" ]
    then
        kill -0 $CURRENT_PID
        exit $?
    else
        exit 3
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    restart|reload|force-reload)
        stop
        start
        ;;
esac