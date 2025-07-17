user=`whoami`
group=`ps -o pgid,cmd -U $user | grep [F]rameGeo | xargs | cut -d" " -f1`
kill -- -$group
xset -d :0 dpms 60 120 120
xset -d :0 dpms force off
