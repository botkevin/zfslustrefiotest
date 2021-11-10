import os
import csv
import argparse
from numpy.core.fromnumeric import size
import pandas
import numpy as np
from matplotlib import pyplot as plt
import scipy.stats as scistats

def plot_data(nj, iodepth, bs, logdata, ax, start):
    logdata = logdata[start:,:]
    mean = np.nanmean(logdata[:,1])
    ax.plot(*logdata.T, label="NJ:%s | IOD:%s | BS:%s || mean:%s"%(nj,iodepth,bs,str(mean)))

def read_log(logfn):
    # print (logfn)
    try:
        logdata = pandas.read_csv(logfn)
    except:
        print ("Missing: " + logfn)
        return np.zeros(shape=(100,2))
    logdata = logdata.to_numpy().astype(float)
    logdata = logdata[:,:2]

    # trim leading and ending zeros
    def np_trim_zeros_2d(arr):
        def find_first_zero(arr):
            for i,a in enumerate(arr[:,1]):
                if a != 0:
                    return i
            return 0
        start = find_first_zero(arr) + 1
        end = arr.shape[0] - find_first_zero(arr[::-1,:]) - 1
        return arr[start:end,:]
    logdata = np_trim_zeros_2d(logdata)


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
                try:
                    with open(output_path, 'r') as f:
                        last_line = f.readlines()[-1]
                        outputs.append ("NJ:%s | IOD:%s | BS:%s"%(nj,iodepth,bs) + last_line)
                except:
                    pass
                mean_data = np.nanmean(log_data[start:,1])
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

# nj, io, bs
def gen_test_mat(results_dict_test, numjobs, blocksizes, iodepths, start=0):
    test_mat = np.zeros(shape=(len(numjobs), len(iodepths), len(blocksizes)))
    print ((len(numjobs), len(iodepths), len(blocksizes)))
    for i, nj in enumerate(numjobs):
        for j, iodepth in enumerate(iodepths):
            for k, bs in enumerate(blocksizes):
                log_data = results_dict_test[nj][iodepth][bs]
                mean_data = np.nanmean(log_data[start:,1])
                test_mat[i,j,k] = mean_data
    return test_mat

def make_plot_from_dict(results_dict_test, parent_dir, testname, numjobs, blocksizes, iodepths, fs, rw, gen_plt=True, start=0, io_choose=None, bs_choose=None, nj_choose=None):
    testdir = parent_dir + "/" + testname
    test_mat = np.zeros(shape=(len(numjobs), len(iodepths), len(blocksizes)))
    avgs = []
    if io_choose:
        iodepths = io_choose
    if bs_choose:
        blocksizes = bs_choose
    if nj_choose:
        numjobs = nj_choose

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
    for i, nj in enumerate(numjobs):
        for j, iodepth in enumerate(iodepths):
            for k, bs in enumerate(blocksizes):
                parent_dir = testdir+"/outputs/"

                log_data = results_dict_test[nj][iodepth][bs]

                # output data is now just data generated from the results_dict
                mean_data = np.nanmean(log_data[start:,1])
                avgs.append ("NJ:%s | IOD:%s | BS:%s"%(nj,iodepth,bs) + " :: " + str(mean_data))

                test_mat[i,j,k] = mean_data
                if gen_plt:
                    plot_data(nj, iodepth, bs, log_data, ax, start)

    if gen_plt:
        ax.legend(bbox_to_anchor=(1.0, 1.05))
    return fig, title, avgs, test_mat

# io depth is same as queue depth (qd)
# TODO:
# avg_io set will plot iodepth=1 and will give the average thruput(over qd) as well as the average difference between IOs and standard deviation for the difference
# bs will do the same this except with blocksize and plot bs=64m
# also should do difference between zfs and lustre speeds
def gen_plots_from_dict(results_dict, csvfilename, skip_num,stop=0, save=True, gen_plt=True, test_dir="tests", start=0, rw_choose=None, fs_choose=None, io_choose=None, bs_choose=None, nj_choose=None, graph_save_dir_prefix=""):
    if rw_choose:
        rws = rw_choose
    else:
        rws = ["read", "write"]
    if fs_choose:
        fss = fs_choose
    else:
        fss = ["zfs", "lustre"]
    avgs_all = []
    figs_all = {}
    mats_all = {}
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
            numjobs, blocksizes, iodepths = numjobs.split(), blocksizes.split(), iodepths.split()
            graph_test_dir = graph_save_dir+testname
            if save: os.system ("mkdir " + graph_test_dir)
            fs_dict = {}
            mats_all[testname] = fs_dict
            for fs in fss:
                rw_dict = {}
                fs_dict[fs] = rw_dict
                for rw in rws:
                    fig, title, avgs, test_mat = make_plot_from_dict(results_dict[testname][fs][rw], test_dir, testname, numjobs, blocksizes,iodepths, fs, rw, gen_plt, start, io_choose, bs_choose, nj_choose)
                    figs_all[testname] = fig

                    # nj, io, bs
                    # test_mat = gen_test_mat(results_dict[testname][fs][rw], numjobs, blocksizes, iodepths)
                    rw_dict[rw] = [test_mat, numjobs, iodepths, blocksizes]
                    # avgs = np.nanmean(test_mat, axis=1)
                    # stds = np.nanstd(test_mat, axis=1)


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
    return figs_all, avgs_all, mats_all

# stat is what we want to compute over, ie (nj, io, bs)
def comp_test_mat(test_mat, testname, stat):
    stat_dict = {'nj':0, 'io':1, 'bs':2}
    axis = stat_dict[stat]
    entry = test_mat
    # these are out statlists
    mat = entry[0]
    # nj, io, bs = entry[stat_axis+1]
    # numjobs = entry[1]
    # iodepths = entry[2]
    # blocksizes = entry[3]
    
    title = testname +" computing over " + stat + ": " + str(entry[axis+1])
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.set_xlabel(stat)
    ax.set_ylabel("MB/s")

    def gen_label_helper (stat_keys, avgs, stds, lin_arr, i, j, a, b):
        avg = avgs[i,j]
        std = stds[i,j]
        slope = lin_arr[i,j,0]
        r_val = lin_arr[i,j,2]
        p_val = lin_arr[i,j,3]
        return "%s:%s | %s:%s"%(stat_keys[0],a,stat_keys[1],b) + " || " + "avg: %1.1f | std:%1.1f | slope:%1.1f | rval:%1.1f | pval:%1.1f"%(avg, std, slope, r_val, p_val)

    stat_dict.pop(stat)
    stat_keys = list(stat_dict.keys())
    stat_axis1 = stat_dict[stat_keys[0]]
    stat_axis2 = stat_dict[stat_keys[1]]
    stat_list1 = entry[stat_axis1 + 1]
    stat_list2 = entry[stat_axis2 + 1]

    avgs = np.nanmean(mat, axis=axis)
    stds = np.nanstd(mat, axis=axis)

    # I know this is disgusting but its just so I can iterate through 2 lists of my choosing by excluding one of (nj, io, bs)
    info_arr = []
    info_arr.append(title)
    
    lin_arr = np.zeros(shape=(len(stat_list1), len(stat_list1), 5))
    x = entry[axis+1]
    rearranged_mat = np.moveaxis(mat, [stat_axis1, stat_axis2], [0,1])
    # print ("mat, rearranged:", mat.shape, rearranged_mat.shape)
    # print ("stat1: ", len(stat_list1))
    # print ("stat2: ", len(stat_list2))
    if axis==2:
        x = [small_x[:-1] for small_x in x]
    x = [int(small_x) for small_x in x]

    for i, a in enumerate(stat_list1):
        for j, b in enumerate(stat_list2):
            # iterate through axis that is not our test stat 
            y = rearranged_mat[i,j,:]
            # vals = slope, intercept, r_value, p_value, std_err
            vals = scistats.linregress (x,y)
            lin_arr[i,j] = vals
            label = gen_label_helper(stat_keys, avgs, stds, lin_arr, i, j, a, b)
            ax.plot (x, y, label=label)
            info_arr.append (label)
    ax.legend(bbox_to_anchor=(1.0, 1.05)) # bbox_to_anchor=(1.0, 1.05)
    return info_arr, lin_arr


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