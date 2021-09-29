import os
import csv

csvfilename = "config.csv"
skip_num = 0

def make_plot_cmd(rw, fs, bs, iodepths, numjobs, testname):
    if fs == "zfs":
        fsdir = 'lustre/lustre/'
    else:
        fsdir = 'zfs/tank/'
    cmd = './fio-plot/fio_plot/fio_plot -T "bandwidth of '+ rw +' on ' + fs + ' ' + testname + ' '+bs+'m" -i z2_one_8_single_'+ fsdir +bs+'m -g -r '+rw+' -t bw -d '+ iodepths +' -n ' + numjobs
    return cmd

with open(csvfilename) as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        next(reader)
        for _ in range(skip_num):
            next(reader)
        for row in reader:
            testname, numberdisks, raidmode, raid0, ashift, compression, recordsize, atime, filesize, benchmark, runtime, blocksizes, iodepths, numjobs = row
            rws = ["read", "write"]
            fss = ["zfs", "lustre"]
            blocksizes = blocksizes.split()
            os.system ("mkdir " + "graph_" + testname)
            for bs in blocksizes:
                os.system ("mkdir bs")
                for fs in fss:
                    for rw in rws:
                        make_plot_cmd (rw, fs, bs, iodepths, numjobs, testname)