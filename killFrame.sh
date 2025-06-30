user=`whoami`
group=`ps -o pgid,cmd -U $user | grep [F]ramegeo | xargs | cut -d" " -f1`
kill -- -$group