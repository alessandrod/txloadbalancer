MAX=$1
DOC_ROOT=/Users/oubiwann/Sites/
FILE_PREFIX=twistd
PORT_PREFIX=700
cd /tmp
for ((NUM = 1; NUM <= $MAX; NUM++))
    do
    rm ${FILE_PREFIX}${NUM}.pid
    rm ${FILE_PREFIX}${NUM}.log
    twistd --pidfile=${FILE_PREFIX}${NUM}.pid web \
        --port=${PORT_PREFIX}${NUM} \
        --path=$DOC_ROOT \
        --logfile=${FILE_PREFIX}${NUM}.log
    done
