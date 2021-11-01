import os
import csv
import argparse
import pandas
import numpy as np
from matplotlib import pyplot as plt

def plot_data(nj, iodepth, bs, logdata, ax, start):
    logdata = logdata[start:,:]
    mean = np.mean(logdata[:,1])
    ax.plot(*logdata.T, label="NJ:%s | IOD:%s | BS:%s || mean:%s"%(nj,iodepth,bs,str(mean)))

def read_log(logfn):
    # print (logfn)
    try:
        logdata = pandas.read_csv(logfn)
    except:
        print ("Missing: " + logfn)
        raise Exception()
    logdata = logdata.to_numpy().astype(float)
    logdata = logdata[:,:2]

    logdata /= 1000 # from millisecond to seconds and KiB/s to MiB/s
    logdata[:,1] *= 1.04858 # from MiB to MB
    # logdata[:,1] /= float(nj) # weird zfs storage recording bug 
    return logdata

def add_title(arr, arr_all, title):
    title_entry = [title]
    title_entry.extend(arr)
    arr_all.append(title_entry)

# reads data and make a plot for one test
def make_plot(parent_dir, testname, numjobs, blocksizes, iodepths, fs, rw, gen_plt=True, start=0):
    testdir = parent_dir + "/" + testname

    results_dict_test = {}
    outputs = []
    avgs=[]
    if gen_plt:
        fig, ax = plt.subplots()
    else:
        fig, ax = None, None
    title = testname.replace("_"," ") + " | " + fs + " " + rw
    if gen_plt:
        ax.set_title(title)
        ax.set_xlabel("seconds")
        ax.set_ylabel("MB/s")
    # first layer is nj
    for nj in numjobs.split():
        io_dict = {}
        results_dict_test[nj] = io_dict
        for iodepth in iodepths.split():
            bs_dict = {}
            io_dict[iodepth] = bs_dict
            for bs in blocksizes.split():
                identifier = fs + "/"+nj + "-"+iodepth + "-"+bs 
                parent_dir = testdir+"/outputs/"

                logfn = testdir+"/bandwidth_logs/" + identifier +"_"+rw+".log"
                log_data = read_log(logfn)
                bs_dict[bs] = log_data

                output_path = parent_dir + identifier + "_"+rw+".txt"
                with open(output_path, 'r') as f:
                    last_line = f.readlines()[-1]
                    outputs.append ("NJ:%s | IOD:%s | BS:%s"%(nj,iodepth,bs) + last_line)
                mean_data = np.mean(log_data[start:,1])
                avgs.append ("NJ:%s | IOD:%s | BS:%s"%(nj,iodepth,bs) + ": " + str(mean_data))
                
                if gen_plt:
                    plot_data(nj, iodepth, bs, log_data, ax, start)
    if gen_plt:
        ax.legend(bbox_to_anchor=(1.0, 1.05))
    return fig, title, outputs, avgs, results_dict_test

# results dict:
# testname, fs, rw, nj, iodepth, bs
def gen_plots(csvfilename, skip_num,stop=0, save=True, gen_plt=True, test_dir="tests", start=0, rw_choose=None, fs_choose=None, graph_save_dir_prefix=""):
    outputs_all = []
    avgs_all = []
    figs_all = []
    results_dict = {}
    if rw_choose:
        rws = rw_choose
    else:
        rws = ["read", "write"]
    if fs_choose:
        fss = fs_choose
    else:
        fss = ["zfs", "lustre"]
    graph_save_dir =  graph_save_dir_prefix + "graphs/"
    if save: os.system ("mkdir " + graph_save_dir)

    with open(csvfilename) as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        next(reader)
        for _ in range(skip_num):
            next(reader)
        stop_counter = 0
        for row in reader:
            testname, numberdisks, raidmode, raid0, ashift, compression, recordsize, atime, filesize, benchmark, runtime, blocksizes, iodepths, numjobs = row
            
            fs_dict = {}
            results_dict[testname] = fs_dict

            graph_test_dir = graph_save_dir+testname
            if save: os.system ("mkdir " + graph_test_dir)

            for fs in fss:
                rw_dict = {}
                fs_dict[fs] = rw_dict

                for rw in rws:
                    fig, title, outputs, avgs, results_dict_test = make_plot (test_dir, testname, numjobs, blocksizes, iodepths, fs, rw, gen_plt,start)
                    rw_dict[rw] = results_dict_test
                    figs_all.append(fig)
                    if save:
                        save_name = title.replace(" ", "-")
                        fig.savefig(graph_test_dir+"/"+save_name)
                    else:
                        # fig.show()
                        pass
                    # TODO: save plot to specific dir
                    add_title(avgs, avgs_all, title)
                    add_title(outputs, outputs_all, title)
            stop_counter += 1
            if stop_counter == stop:
                return figs_all, outputs_all, results_dict
    return figs_all, outputs_all, avgs_all, results_dict

def make_plot_from_dict(results_dict_test, parent_dir, testname, numjobs, blocksizes, iodepths, fs, rw, gen_plt=True, start=0):
    testdir = parent_dir + "/" + testname

    avgs = []
    if gen_plt:
        fig, ax = plt.subplots()
    else:
        fig, ax = None, None
    title = testname.replace("_"," ") + " | " + fs + " " + rw
    if gen_plt:
        ax.set_title(title)
        ax.set_xlabel("seconds")
        ax.set_ylabel("MB/s")
    # first layer is nj
    for nj in numjobs.split():
        for iodepth in iodepths.split():
            for bs in blocksizes.split():
                identifier = fs + "/"+nj + "-"+iodepth + "-"+bs 
                parent_dir = testdir+"/outputs/"

                log_data = results_dict_test[nj][iodepth][bs]

                # output data is now just data generated from the results_dict
                mean_data = np.mean(log_data[start:,1])
                avgs.append ("NJ:%s | IOD:%s | BS:%s"%(nj,iodepth,bs) + ": " + str(mean_data))
                if gen_plt:
                    plot_data(nj, iodepth, bs, log_data, ax, start)
    if gen_plt:
        ax.legend(bbox_to_anchor=(1.0, 1.05))
    return fig, title, avgs

# io depth is same as queue depth (qd)
# TODO:
# avg_io set will plot iodepth=1 and will give the average thruput(over qd) as well as the average difference between IOs and standard deviation for the difference
# bs will do the same this except with blocksize and plot bs=64m
# also should do difference between zfs and lustre speeds
def gen_plots_from_dict(results_dict, csvfilename, skip_num,stop=0, save=True, gen_plt=True, test_dir="tests", start=0, rw_choose=None, fs_choose=None, avg_io=False, graph_save_dir_prefix=""):
    if rw_choose:
        rws = rw_choose
    else:
        rws = ["read", "write"]
    if fs_choose:
        fss = fs_choose
    else:
        fss = ["zfs", "lustre"]
    avgs_all = []
    figs_all = []
    graph_save_dir =  graph_save_dir_prefix + "graphs/"
    if save: os.system ("mkdir " + graph_save_dir)
    with open(csvfilename) as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        next(reader)
        for _ in range(skip_num):
            next(reader)
        stop_counter = 0
        for row in reader:
            testname, numberdisks, raidmode, raid0, ashift, compression, recordsize, atime, filesize, benchmark, runtime, blocksizes, iodepths, numjobs = row
            graph_test_dir = graph_save_dir+testname
            if save: os.system ("mkdir " + graph_test_dir)
            outputs_one_test = []
            for fs in fss:
                for rw in rws:
                    fig, title, avgs = make_plot_from_dict(results_dict[testname][fs][rw], test_dir, testname, numjobs, blocksizes, iodepths, fs, rw, gen_plt=gen_plt, start=start)
                    figs_all.append(fig)
                    if save:
                        save_name = title.replace(" ", "-")
                        fig.savefig(graph_test_dir+"/"+save_name)
                    else:
                        # fig.show()
                        pass
                    add_title(avgs, avgs_all, title)
            stop_counter += 1
            if stop_counter == stop:
                return figs_all, avgs_all
    return figs_all, avgs_all

def print_info_arr(arr):
    for one_test in arr:
        print ('------------------') # test divider
        for line in one_test:
            print (line)

def get_args():
    parser = argparse.ArgumentParser(description='run io tests from specified config')
    parser.add_argument ('--csv', type=str, default='config.csv', dest='csvfilename')
    parser.add_argument ('--skip_num', '-s', type=int, default=0, dest='skip_num')
    parser.add_argument ('--stop', type=int, default=0, dest='stop')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = get_args()
    # TODO: 