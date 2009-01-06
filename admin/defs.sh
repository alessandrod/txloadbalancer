LIB=txlb
BZR=lp:txloadbalancer
#BZR='lp:~oubiwann/txloadbalancer/1.1.0'
echo $BZR_DEST
FLAG='skip_tests'
MSG=commit-msg
export PYTHONPATH=.:./test:$PYTHONPATH

function getDiff {
    bzr diff $1 | \
        egrep '^\+' | \
        sed -e 's/^\+//g'| \
        egrep -v "^\+\+ ChangeLog"
}

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
    rm -rf $MSG _trial_temp test.out .DS_Store CHECK_THIS_BEFORE_UPLOAD.txt
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
    echo "Pushing to Launchpad now ($BZR) ..."
    bzr push $BZR && pushSucceed
    cleanup
}

function buildSucceed {
    echo "Build succeeded."
    echo "Cleaning up files ..."
    ./admin/clean.sh
    echo "Done."
    echo
}
