; Even detector
readdisk 0 0x0001 ; the location in disk where our value is stored
loadram 1 0
shift 1 1 1 1 1
cmpic 1 0
jmprellz 3

printc 0
halt

printc 1
halt