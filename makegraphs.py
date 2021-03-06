import os
import csv
import argparse

def make_plot_cmd(rw, fs, bs, iodepths, numjobs, testname, recordsize):
    if fs == "zfs":
        fsdir = '/lustre/'
    else:
        fsdir = '/tank/'
    title = 'bandwidth of '+ rw +' on ' + fs + ' ' + testname + ' '+bs
    if recordsize != '128k':
        title += recordsize
    cmd = './fio-plot/fio_plot/fio_plot -T "' + title + '" -i '+ testname + fsdir +bs+' -g -r '+rw+' -t bw -d '+ iodepths +' -n ' + numjobs + ' --disable-fio-version'
    return cmd, title

def make_commands(csvfilename, skip_num,stop=0):
    cmds = []
    with open(csvfilename) as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        next(reader)
        for _ in range(skip_num):
            next(reader)
        stop_counter = 0
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
                        plot_cmd, title = make_plot_cmd (rw, fs, bs, iodepths, numjobs, testname, recordsize)
                        title = title.replace(" ", "-")
                        cmds.append (plot_cmd)
                        cmds.append ("mv " + title + '* ' + blockdir)
                        # TODO: save plot to specific dir
            stop_counter += 1
            if stop_counter == stop:
                return cmds
    return cmds

def get_args():
    parser = argparse.ArgumentParser(description='run io tests from specified config')
    parser.add_argument ('--csv', type=str, default='config.csv', dest='csvfilename')
    parser.add_argument ('--skip_num', '-s', type=int, default=0, dest='skip_num')
    parser.add_argument ('--stop', type=int, default=0, dest='stop')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = get_args()
    # TODO: stop to param
    # set stop to 0 if you don't need it
    stop = 0
    cmds = make_commands(args.csvfilename, args.skip_num, args.stop)
    for cmd in cmds:
        os.system (cmd)