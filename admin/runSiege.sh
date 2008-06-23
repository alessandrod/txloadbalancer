# This script will generate a files with rows of data having the following
# columns, in order:
#
#  1) Sample Count
#  2) Attempted Concurrency
#  3) Elapsed Time
#  4) Transaction Rate
#  5) Throughput
#  6) Concurrency
#  7) Successful Transactions
#  8) Failed Transactions
#  9) CPU Count
#  10) Twisted Daemon Count
#  11) Is Loadbalanced?
#  12) Balanced Host Count
#
LOG="data/stats.csv"
#URL="http://lorien:8080/index.html"
URL="http://fangorn:6080/index.html"
LB="yes"
LB_HOSTS=2
WEB_SERVERS=4
TOTAL_CPUS=4
TIME=10s
REST=5
SAMPLES=10
RANGE="1 2 5 10 20 30 40 50 60 70 80 90 100"
for CONCUR in $RANGE
    do
    for ((SAMPLE=1; SAMPLE <= $SAMPLES; SAMPLE++))
        do
        DATA=`siege -c $CONCUR -b -t $TIME $URL 2>&1 | \
            egrep 'Successful|Concurrency:|rate:|Failed|Elapsed|Throughput:' | \
            awk -F: '{print $2}' | \
            awk '{print $1 ","}'`
        OUT="$SAMPLE, $CONCUR, $DATA $TOTAL_CPUS, $WEB_SERVERS, $LB, $LB_HOSTS"
        echo $OUT >> $LOG
        sleep $REST
        done
    done
