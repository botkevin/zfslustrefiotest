import os
import csv

csvfilename = "config.csv"
skip_num = 6

def make_plot_cmd(rw, fs, bs, iodepths, numjobs, testname):
    if fs == "zfs":
        fsdir = '/lustre/lustre/'
    else:
        fsdir = '/zfs/tank/'
    title = 'bandwidth of '+ rw +' on ' + fs + ' ' + testname + ' '+bs
    cmd = './fio-plot/fio_plot/fio_plot -T "' + title + '" -i '+ testname + fsdir +bs+' -g -r '+rw+' -t bw -d '+ iodepths +' -n ' + numjobs + '--disable-fio-version'
    return cmd, title

def make_commands():
    cmds = []
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
            # print (blocksizes)
            graphdir = "graph_" + testname
            cmds.append ("mkdir " + graphdir)
            for bs in blocksizes:
                blockdir = graphdir +"/"+bs
                cmds.append ("mkdir "+ blockdir)
                for fs in fss:
                    for rw in rws:
                        plot_cmd, title = make_plot_cmd (rw, fs, bs, iodepths, numjobs, testname)
                        title = title.replace(" ", "-")
                        cmds.append (plot_cmd)
                        cmds.append ("mv " + title + '* ' + blockdir)
                        # TODO: save plot to specific dir
    return cmds

if __name__ == "__main__":
    cmds = make_commands()
    for cmd in cmds:
        os.system (cmd)