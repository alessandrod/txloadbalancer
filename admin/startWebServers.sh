STARTING_PORT=$1
ENDING_PORT=$2
DOC_ROOT=/Users/oubiwann/Sites/
#DOC_ROOT=/home/oubiwann/public_html/
FILE_PREFIX=/tmp/twistd
cd /tmp
for ((NUM=$STARTING_PORT; NUM <= $ENDING_PORT; NUM++))
    do
    echo "Removing old pid and log files..."
    rm ${FILE_PREFIX}${NUM}.pid
    rm ${FILE_PREFIX}${NUM}.log
    echo "Starting up twistd on $NUM..."
    twistd --pidfile=${FILE_PREFIX}${NUM}.pid web \
        --port=${NUM} \
        --path=$DOC_ROOT \
        --logfile=${FILE_PREFIX}${NUM}.log
    done
