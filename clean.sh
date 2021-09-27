umount -f 192.168.169.207@tcp:/test
umount mgsmdt/mgsmdt
umount tank/ost0
tunefs.lustre --writeconf mgsmdt/mgsmdt
tunefs.lustre --writeconf tank/ost0
zpool destroy -f tank

