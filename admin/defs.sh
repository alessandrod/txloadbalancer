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
