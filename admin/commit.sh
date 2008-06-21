LIB=./txlb/
BZR=lp:txloadbalancer
FLAG='skip_tests'
MSG=commit-msg
export PYTHONPATH=.:./test

function abort {
    echo "*** Aborting rest of process! ***"
    exit
}

function error {
    echo "There was an error committing/pushing; temp files preserved."
    abort
}

function cleanup {
    echo "Cleaning up temporary files ..."
    rm $MSG
    rm -rf _trial_temp
    rm test.out
    echo "Done."
}

function localCommit {
    echo "Committing locally ..."
    bzr commit --local --file $MSG
}

function pushSucceed {
    echo "Push succeeded."
}

function pushLaunchpad {
    echo "Pushing to Launchpad now ..."
    bzr push $BZR && pushSucceed
    cleanup
}

bzr diff ChangeLog | \
    egrep '^\+' | \
    sed -e 's/^\+//g'| \
    egrep -v '^\+\+ ChangeLog' > $MSG
echo "Committing with this message:"
cat $MSG
echo
if [[ "$1" == "$FLAG" ]];then
    echo 'OK' > test.out
else
    # send the output (stdout and stderr) to both a file for checking and
    # stdout for immediate viewing/feedback purposes
    trial $LIB 2>&1|tee test.out
fi
STATUS=`tail -1 test.out|grep 'FAIL'`
if [[ "$STATUS" == '' ]];then
    if [[ "$1" == "FLAG" ]];then
        echo "Skipping tests..."
    else
        echo "All tests passed."
    fi
    localCommit && pushLaunchpad || error
else
    abort
fi
