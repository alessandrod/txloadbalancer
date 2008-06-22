MAX=$1
#DOC_ROOT=/Users/oubiwann/Sites/
DOC_ROOT=/home/oubiwann/public_html
FILE_PREFIX=twistd
STARTING_PORT=7001
cd /tmp
for ((NUM=$STARTING_PORT; NUM <= $MAX; NUM++))
    do
    rm ${FILE_PREFIX}${NUM}.pid
    rm ${FILE_PREFIX}${NUM}.log
    twistd --pidfile=${FILE_PREFIX}${NUM}.pid web \
        --port=${NUM} \
        --path=$DOC_ROOT \
        --logfile=${FILE_PREFIX}${NUM}.log
    done
