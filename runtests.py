import numpy as np
import os
import csv
import sys
import argparse

# STATICS
RAID_CONFIGS = {
    5:"raidz",
    6:"raidz2",
    7:"raidz3",
    0:"",
    1:"mirror"
}

ALPHABET = alphabets=[str(chr(ord('a')+i)) for i in range(26)]

# this really isnt a static
# TODO: change this to a parameter
SKIP_ZFS_TESTS = False

# Parameters
# not just examples, these are used in code, others are defaults that change based on config.csv
# **********************
ioengine_ = "psync"
startdisk_ = "c"
# there may be some glitches with loginterval < 1000
loginterval_ = "1250"
# **********************
# rest are defaults that are not used
numberdisks_ = 1
zfsname_ = "tank"
raidmode_ = 0
# do we want the raid in +0 config, 
#   IE if we want raid50 with 2 raid 5 volumes in raid 0 config,
#   we have raidmode=5, raid0=2
raid0_ = 0

# zfs-options
ashift_ = "12"
compression_ = None # this may or may not work with our datasets, perhaps we can try lz4 (no overhead)
recordsize_ = "128k" # zfs default
atime_ = "on" # zfs default

testname_ = "onedisk"
filesize_ = "100g"
runtime_ = "200"

# meat meat meat
# ---------------------------------------------------------------------------------------------------------------

def make_zfs(startdisk, numberdisks, zfsname, raidmode, raid0, ashift, compression, recordsize, atime):
    raidmodestr = raidmode if type(raidmode)==str else RAID_CONFIGS[raidmode]
    cmdstr = "zpool create " + zfsname

    propertiesstr = " -o ashift="+ashift
    # if use compression
    #     propertiesstr += " -o compression="+compression

    disks = []
    start = ord(startdisk[-1]) - ord('a')
    for i in range(start, start + numberdisks):
        j = i//26 - 1
        start = "" if j<0 else ALPHABET[j]
        disks.append ("sd" + start+ALPHABET[i%26])
    disksstr = ""
    for i, disk in enumerate(disks,0):
        if raid0!=0 and i%(numberdisks//raid0)==0 and i != 0:
            disksstr += " " + raidmodestr
        disksstr += " " + disk
    
    cmdstr += propertiesstr
    cmdstr += " " + raidmodestr
    cmdstr += disksstr
    options_cmd = 'zfs set recordsize='+recordsize + ' atime='+atime + ' ' + zfsname
    return [cmdstr, options_cmd]

# blocksizes, iodepths, and numjobs are just lists delimited by spaces ex: "1 2 3"
def make_fio_thruput(dir, testname, filesize, benchmark, runtime, blocksizes, iodepths, numjobs, fs="zfs"):
    if benchmark == "FALSE":
        # no benchmark is deprecated option
        options = " --direct=1 --bs=32m --ioengine="+ioengine_+" --iodepth=64 --filesize="+filesize+" --group_reporting --name=throughput-test --eta-newline=1"
        writecmd = "fio --directory="+ dir                          + options + " --rw=write >> " + testname + "/" + fs + "_write.txt"
        readcmd  = "fio --filename="+ dir + "/throughput-test.0.0" + options + "--rw=read --readonly >> " + testname + "/" + fs + "_read.txt"
        rmcmd = "rm "+ dir +"/throughput-test.0.0"
        return writecmd, readcmd, rmcmd
    else:
        options = "--target " + dir + " -o "+testname+" -b "+blocksizes+" --iodepth "+iodepths+" --numjobs "+numjobs+" --size "+filesize+" --runtime "+runtime+" --engine "+ioengine_+" --loginterval "+loginterval_
        cmd = "./bench_fio  --type directory --quiet -m write read --loops 1 " + options
        return [cmd]

# need to make sure that:
# I don't know if this is needed? see 
# /etc/ldev.conf is changed:
# hostname - mgs     zfs:lustre-mgs/mgs
# hostname - mdt0    zfs:lustre-mdt0/mdt0
# hostname - ost0    zfs:lustre-ost0/ost0
# SELinux is disabled: sed -i '/^SELINUX=/s/.*/SELINUX=disabled/' /etc/selinux/config 
# see the vms for what we did with ldev.conf for remote connections
#
# lustre is started:
# systemctl start lustre
# ost dir should not 
def make_lustre(zfsname, mgsmdtname="mgsmdt", ip="$(hostname)", protocol="tcp"):
    #fs name is test btw
    full_ip = ip +"@"+ protocol
    cmds = []
    cmds.append("mkfs.lustre --backfstype=zfs --fsname=test --index=0 --reformat --mgs --mdt "+ mgsmdtname +"/mgsmdt") # mgsmdt should be static
    cmds.append("mkfs.lustre --backfstype=zfs --fsname=test --index=0 --ost --mgsnode="+ full_ip + " " + zfsname +"/ost0")
    # mount
    lustre_mount = "mount -t lustre "
    cmds.append(lustre_mount + mgsmdtname +"/mgsmdt /mnt/mgsmdt")
    cmds.append(lustre_mount + zfsname +"/ost0 /mnt/ost")
    cmds.append(lustre_mount + full_ip + ":/test" + " /mnt/lustre")

    # don't need this because its all mounted already. Should we remount? probably don't need to remount, but might as well... 
    # lustre client mount 
    # mount -t lustre <MGS node>
    #     /<fsname> <mount point>
    # ex:  mount -t lustre 192.168.169.207@tcp:/test /mnt/lustre
    return cmds

def clean(zfsname, mgsmdtname="mgsmdt", ip="$(hostname)", protocol="tcp"):
    full_ip = ip +"@"+ protocol
    devices = [mgsmdtname +"/mgsmdt", zfsname +"/ost0"]
    cmds = []
    # lustre
    cmds.append("umount -f "+ full_ip + ":/test")
    for device in devices:
        cmds.append("umount "+ device)
    for device in devices:
        cmds.append("tunefs.lustre --writeconf " + device)
    # zfs
    cmds.append ("zpool destroy -f "+ zfsname)
    return cmds
    
def make_echo(msg):
    line = "echo -------------------------------"
    return line, "echo "+msg, line

def print_title(msg):
    line = "-------------------------------"
    print (" "+line, "\n  ", msg, "\n", line)

def make_commands(startdisk, numberdisks, zfsname, raidmode, raid0, ashift, compression, recordsize, atime, testname, ip, filesize, benchmark, runtime, blocksizes, iodepths, numjobs):
    zfsdir = "/"+zfsname
    cmds = []
    cmds.append ("mkdir " + testname)
    
    cmds.extend (make_echo("make zfs"))
    cmds.extend (make_zfs(startdisk, numberdisks, zfsname, raidmode, raid0, ashift, compression, recordsize, atime))
    
    # arugments to make_fio_througput: dir, testname, filesize, benchmark, runtime, blocksizes, iodepths, numjobs, fs="zfs"
    if not SKIP_ZFS_TESTS:
        cmds.extend (make_echo("test zfs"))
        cmds.extend (make_fio_thruput(zfsdir, testname, filesize, benchmark, runtime, blocksizes, iodepths, numjobs, fs="zfs"))

    cmds.extend (make_echo("make lustre"))
    lustrecmds = make_lustre(zfsname, ip=ip)
    cmds.extend (lustrecmds)

    cmds.extend (make_echo("test lustre"))
    cmds.extend (make_fio_thruput("/mnt/lustre", testname,filesize, benchmark, runtime, blocksizes, iodepths, numjobs, fs="lustre"))

    cmds.extend (make_echo("cleanup"))
    cmds.extend (clean(zfsname, ip=ip))
    return cmds

# ---------------------------------------------------------------------------------------------------------------

def run_one(startdisk, numberdisks, zfsname, raidmode, raid0, ashift, compression, recordsize, atime, testname, ip, filesize, benchmark, runtime, blocksizes, iodepths, numjobs):
    cmds = make_commands(startdisk, numberdisks, zfsname, raidmode, raid0, ashift, compression, recordsize, atime, testname, ip, filesize, benchmark, runtime, blocksizes, iodepths, numjobs)
    for cmd in cmds:
        # debug print
        print (cmd)
        os.system(cmd)

def run_all(startdisk, zfsname, csvfilename, ip, skip_num=0):
    with open(csvfilename) as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        next(reader)
        for _ in range(skip_num):
            next(reader)
        for row in reader:
            testname, numberdisks, raidmode, raid0, ashift, compression, recordsize, atime, filesize, benchmark, runtime, blocksizes, iodepths, numjobs = row
            print ("++++++++++++++++++++++++++++")
            print (testname)
            print ("++++++++++++++++++++++++++++")
            numberdisks = int(numberdisks)
            raidmode = int(raidmode)
            raid0 = int(raid0)
            run_one(startdisk, numberdisks, zfsname, raidmode, raid0, ashift, compression, recordsize, atime, testname, ip, filesize, benchmark, runtime, blocksizes, iodepths, numjobs)

def get_args():
    parser = argparse.ArgumentParser(description='run io tests from specified config')
    parser.add_argument ('--csv', type=str, default='config.csv', dest='csvfilename')
    parser.add_argument ('--ip', type=str, default='192.168.169.207', dest='ip')
    parser.add_argument ('--skip_num', '-s', type=int, default=0, dest='skip_num')
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    # skip_num is 11 for what we want 10/14
    args = get_args()
    try:
        run_all(startdisk_, zfsname_, args.csvfilename, args.ip, skip_num=args.skip_num)
    # this doesn't work... just use "pgrep python" then "kill -9 <PID>"
    except KeyboardInterrupt:
        print("\nControl-C pressed - quitting...")
        os.system("./clean.sh")
        sys.exit(1)