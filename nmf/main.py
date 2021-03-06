import os
import sys
from datetime import datetime
import numpy as np
import pandas as pd
from nmf import io, util, metric, algorithm, noise
from util import error_vs_iter
import matplotlib.pyplot as pl

#from functools import partial
import multiprocessing
from itertools import repeat
import time
from numba import jit
from numba import vectorize, float64, int64

# Configuration
sample_size = 0.9
epoch = 40
random_state = 0
parallel_flag = 0

scale = { "ORL": 3, "CroppedYaleB": 4}
img_size = {"ORL": (92, 112), "CroppedYaleB": (168, 192)}

niter = {
    "Multiplication KL Divergence": 1200,
    "Multiplication Euclidean": 500,
    #"Multiplication Euclidean regularized": 500,
}

min_error = {
    "Multiplication KL Divergence": 2.3,
    "Multiplication Euclidean": 200,
    #"Multiplication Euclidean regularized": 200,
}
model = {
    #"Benchmark (scikit-learn)": algorithm.benchmark,
    "Multiplication KL Divergence": algorithm.multiplication_divergence,
    "Multiplication Euclidean": algorithm.multiplication_euclidean,
    #"Multiplication Euclidean regularized": algorithm.multiplication_euclidean_regularized,
}

Noise = {
    "No Noise": noise.identity,
    "Poisson": noise.possion,
    "Normal": noise.normal,
    "Salt and Pepper": noise.salt_and_pepper,
}

rnd = np.random.RandomState()

def main():
    """Run NMF on CroppedYaleB and ORL dataset."""
    
    argvs = ['hi',"croppedYale"]
    message = "Please choose one of the two datasets: 'orl' or 'croppedYale'"
    if len(argvs) < 2:
       print(message)
       sys.exit()
    assert argvs[-1] in ["orl", "croppedYale"], message
    # argvs = ["orl"]
    # make a folder with generated time
    folder = datetime.now().strftime("%Y-%m-%d-%H-%M")
    folder = os.path.join("results", folder + "-" + argvs[-1])
    if not os.path.exists(folder):
        os.makedirs(folder)
    if argvs[-1] == "orl":
        if os.name == 'nt':
            #train("..\\data\\ORL", folder)
            train("data" + os.sep + "ORL", folder)
            # train("data/CroppedYaleB")
        else:
            train("data"+os.sep+"ORL", folder)
            # train("data/CroppedYaleB")
    else:
        if os.name == 'nt':
            #train("..\\data\\CroppedYaleB", folder)
            train("data" + os.sep + "CroppedYaleB", folder)
        else:
            train("data" + os.sep + "CroppedYaleB", folder)



def one_simulation(i,Vhat,Yhat,n,size,metrics,folder):
    # sample 90% of samples
    index = rnd.choice(np.arange(n), size, replace=False)
    subVhat, subYhat = Vhat[:, index], Yhat[index]
    for noise_fun in Noise:
        # add noise
        V, V_noise = Noise[noise_fun](subVhat)
        n_samples = len(Vhat)

        # global centering
        #V = V - V.mean(axis=0)
        # local centering
        #V -= V.mean(axis=1).reshape(n_samples, -1)
        #V -= V.min()
        #V = V / V.max()
        # number of clusters
        r = np.unique(Yhat).shape[0]

        # loop through different models
        for name, algo in model.items():
            name2=name
            name=name+' '+noise_fun
            ncpu=os.cpu_count()
            pool = multiprocessing.Pool(ncpu)
            m=Vhat.shape[0]
            n=Vhat.shape[1]
            #W0=[np.random.rand(m,r) for i in range(ncpu)]
            #H0=[np.random.rand(r,n) for i in range(ncpu)]

            args = zip(repeat(V,ncpu), repeat(r,ncpu),repeat(niter[name2],ncpu),repeat(min_error[name2],ncpu))
            result = pool.starmap(algo, args)
            #import IPython; IPython.embed()
            pool.close()
            pool.join()
            errors_n=[i[2][-1] for i in result]
            W, H, errors = result[errors_n.index(min(errors_n))]
            #W, H, errors = algo(V, r, niter[name2], min_error[name2])
            # save subVhat, V and H to disk - only epoch1
            if i == 0:
                path_matrix = os.path.join(folder, "matrix_{}".format(name))
                print("Saving to {}.npz".format(path_matrix))
                np.save(path_matrix, (subVhat, V, V_noise,  W.dot(H)))
            # plot error versus iteration only when non-paralle
            if parallel_flag == 0:
                data_name = folder.split("-")[-1]
                plotname = "{}_{}_Error_{}_Iteration".format(data_name, name2,
                                                             niter[name2])
                path = os.path.join(folder, plotname)
                error_vs_iter(errors, niter[name2], name2, path)
                # save errors to disk as well
                error_df = pd.DataFrame({"Errors": errors})
                error_df.to_csv("{}.csv".format(path), index=False)
            Ypred = util.assign_cluster_label(H.T, subYhat)

            # evaluate metrics
            _rre = metric.eval_rre(subVhat, W, H)
            _acc = metric.eval_acc(subYhat, Ypred)
            _nmi = metric.eval_nmi(subYhat, Ypred)
            print("Epoch = {}, Model = {}, RRE = {}".format(i + 1, name, _rre))
            print("Epoch = {}, Model = {}, ACC = {}".format(i + 1, name, _acc))
            print("Epoch = {}, Model = {}, NMI = {}".format(i + 1, name, _nmi))
            metrics["rre"][name].append(_rre)
            metrics["acc"][name].append(_acc)
            metrics["nmi"][name].append(_nmi)
    return metrics


def train(data_name, folder):
    """Run NMF on data stored in data_name."""
    # load ORL dataset
    print("==> Load {} dataset...".format(data_name))
    Vhat, Yhat = io.load_data(data_name, scale[data_name.split(os.sep)[-1]])
    n = len(Yhat)
    size = int(n * sample_size)
    empty_metric = make_metrics()
    t = time.time()
    if parallel_flag:
        pool = multiprocessing.Pool(os.cpu_count())
        #sim=partial(one_simulation,Vhat=Vhat,Yhat=Yhat,n=n,size=size,metrics=metrics)
        #pool.starmap(sim, (range(epoch),))
        args = zip(range(epoch), repeat(Vhat), repeat(Yhat),
                   repeat(n), repeat(size), repeat(empty_metric), repeat(folder))
        result = pool.starmap(one_simulation, args)
        pool.close()
        pool.join()
    else:
        result = []
        for i in range(epoch):
            empty_metric = make_metrics()
            temp = one_simulation(i, Vhat, Yhat, n, size, empty_metric, folder)
            result.append(temp)
    t = time.time() - t
    print('done with time {} second'.format(t))

    # merge results together
    metrics = make_metrics()
    for dic in result:
        for metric_nm in dic:
            for model_nm in dic[metric_nm]:
                metrics[metric_nm][model_nm] += dic[metric_nm][model_nm]

    # get mean of metrics over epochs and save to disk
    mean_metrics = make_metrics()
    for metric_nm in metrics:
        for model_nm in metrics[metric_nm]:
            average = np.mean(metrics[metric_nm][model_nm])
            mean_metrics[metric_nm][model_nm] = average
    average_df = pd.DataFrame.from_dict(mean_metrics)
    average_df.to_csv(os.path.join(folder, 'statistics_large.csv'))
    print("Average of metrics: ")
    print(average_df)

    # split raw results and save to disk
    for metric_nm in metrics:
        filename = os.path.join(folder, 'raw_result_{}.csv'.format(metric_nm))
        raw = metrics[metric_nm]
        raw_df = pd.DataFrame.from_dict(raw).T
        raw_df = raw_df.reset_index()
        print("Saving to", filename)
        raw_df.to_csv(filename, header=False, index=False)

    # draw metrics comparison and save to folder
    for metric_nm in metrics:
        fig = pl.figure(figsize=(15, 6))
        ax = pl.subplot(111)
        for model_nm in metrics[metric_nm]:
            scores = metrics[metric_nm][model_nm]
            #if metric_nm == "rre":
            #    scores = np.log(scores)
            ax.plot(range(epoch), scores, label=model_nm)
        ax.set_xlabel("epoch")
        ax.set_ylabel(metric_nm)
        ax.set_title("Model comparison of {}".format(metric_nm))
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        plot_name = os.path.join(folder, "metrics_{}".format(metric_nm))
        print("Saving to {}".format(plot_name))
        pl.savefig(plot_name+'.pdf')
        pl.savefig(plot_name+'.eps')


def make_metrics():
    """Make an empty metrics dictionary."""
    metrics = {"rre": {}, "acc": {}, "nmi": {}}
    for noise_fun in Noise:
        for name in model:
            name=name+' '+noise_fun
            metrics["rre"][name] = []
            metrics["acc"][name] = []
            metrics["nmi"][name] = []
    return metrics


if __name__ == "__main__":
    main()
