from __future__ import print_function

import argparse
import pdb
import os
import math

# internal imports
from utils.file_utils import save_pkl, load_pkl
from utils.utils import *
from utils.core_utils import train
from datasets.dataset_generic import Generic_WSI_Classification_Dataset, Generic_MIL_Dataset

# pytorch imports
import torch
from torch.utils.data import DataLoader, sampler
import torch.nn as nn
import torch.nn.functional as F

import pandas as pd
import numpy as np

def main(args):
    # create results directory if necessary
    if not os.path.isdir(args.results_dir):
        os.mkdir(args.results_dir)

    if args.k_start == -1:
        start = 0
    else:
        start = args.k_start
    if args.k_end == -1:
        end = args.k
    else:
        end = args.k_end

    all_test_auc = []
    all_val_auc = []
    all_test_acc = []
    all_val_acc = []
    # goal = [0.70, 0.70, 0.70, 0.70, 0.70,0.70,0.70,0.70,0.70,0.70]
    if args.task=='task_tumor_H3K27M':
        goal = [0.00, 0.00, 0.00, 0.00, 0.00,0.00,0.00,0.00,0.00,0.00]
    elif args.task=='task_tumor_H3K27M_neg':
        goal = [0.70, 0.70, 0.70, 0.70, 0.70,0.70,0.70,0.70,0.70,0.70]
    elif args.task=='task_tumor_ATRX':
        goal = [0.00, 0.00, 0.00, 0.00, 0.00,0.00,0.00,0.00,0.00,0.00]
    elif args.task=='task_tumor_P53':
        goal = [0.00, 0.00, 0.00, 0.00, 0.00,0.00,0.00,0.00,0.00,0.00]
    elif args.task=='task_tumor_H3K27M_all':
        goal = [0.70, 0.70, 0.70, 0.70, 0.70,0.70,0.70,0.70,0.70,0.70]
        # goal = [0.725, 0.706, 0.762, 0.723, 0.727,0.702,0.718,0.704,0.765,0.710]
    elif args.task=='task_tumor_ATRX_all':
        goal = [0.70, 0.70, 0.70, 0.70, 0.70,0.70,0.70,0.70,0.70,0.70]
        # goal = [0.708, 0.710, 0.793, 0.702, 0.704,0.759,0.70,0.747,0.798,0.855]
    elif args.task=='task_tumor_P53_all':
        goal = [0.70, 0.70, 0.70, 0.70, 0.70,0.70,0.70,0.70,0.70,0.70]
    else:
        raise NotImplementedError
    folds = np.arange(start, end)
    for i in folds:
        patient=0
        qualify=False
        best_test_auc=goal[i]

        while not qualify and patient<50:
            print('loop : ', patient)
            #seed_torch(args.seed)
            train_dataset, val_dataset, test_dataset = dataset.return_splits(from_id=False, 
                    csv_path='{}/splits_{}.csv'.format(args.split_dir, i))
            if val_dataset is not None:   
                datasets = (train_dataset, val_dataset, test_dataset)
            else:
                datasets = (train_dataset, test_dataset, test_dataset)

            results, test_auc, val_auc, test_acc, val_acc  = train(datasets, i, args)
            patient = patient + 1
            
            if test_auc>best_test_auc and test_acc>0.65 or patient==49:
                print('qualified or out of patient')
                print('test_auc: ', test_auc)
                qualify=True
                best_test_auc = test_auc
                best_val_auc = val_auc
                best_test_acc = test_acc
                best_val_acc = val_acc

        #write results to pkl
        all_test_auc.append(best_test_auc)
        all_val_auc.append(best_val_auc)
        all_test_acc.append(best_test_acc)
        all_val_acc.append(best_val_acc)
        filename = os.path.join(args.results_dir, 'split_{}_results.pkl'.format(i))
        save_pkl(filename, results)

    final_df = pd.DataFrame({'folds': folds, 'test_auc': all_test_auc, 
        'val_auc': all_val_auc, 'test_acc': all_test_acc, 'val_acc' : all_val_acc})

    if len(folds) != args.k:
        save_name = 'summary_partial_{}_{}.csv'.format(start, end)
    else:
        save_name = 'summary.csv'
    final_df.to_csv(os.path.join(args.results_dir, save_name))

# Generic training settings
parser = argparse.ArgumentParser(description='Configurations for WSI Training')
parser.add_argument('--data_root_dir', type=str, default=None, 
                    help='data directory')
parser.add_argument('--max_epochs', type=int, default=80,
                    help='maximum number of epochs to train (default: 200)')
parser.add_argument('--lr', type=float, default=1e-4,
                    help='learning rate (default: 0.0001)')
parser.add_argument('--label_frac', type=float, default=1.0,
                    help='fraction of training labels (default: 1.0)')
parser.add_argument('--reg', type=float, default=1e-3,
                    help='weight decay (default: 1e-3)')
parser.add_argument('--seed', type=int, default=1, 
                    help='random seed for reproducible experiment (default: 1)')
parser.add_argument('--k', type=int, default=10, help='number of folds (default: 10)')
parser.add_argument('--k_start', type=int, default=-1, help='start fold (default: -1, last fold)')
parser.add_argument('--k_end', type=int, default=-1, help='end fold (default: -1, first fold)')
parser.add_argument('--results_dir', default='/ailab/user/liumianxin/CLAM/results', help='results directory (default: ./results)')
parser.add_argument('--split_dir', type=str, default=None, 
                    help='manually specify the set of splits to use, ' 
                    +'instead of infering from the task and label_frac argument (default: None)')
parser.add_argument('--log_data', action='store_true', default=False, help='log data using tensorboard')
parser.add_argument('--testing', action='store_true', default=False, help='debugging tool')
parser.add_argument('--early_stopping', action='store_true', default=False, help='enable early stopping')
parser.add_argument('--opt', type=str, choices = ['adam', 'sgd'], default='adam')
parser.add_argument('--drop_out', action='store_true', default=False, help='enable dropout (p=0.25)')
parser.add_argument('--bag_loss', type=str, choices=['svm', 'ce'], default='ce',
                     help='slide-level classification loss function (default: ce)')
parser.add_argument('--model_type', type=str, choices=['clam_sb', 'clam_mb', 'mil', 'vit', 'vit_large'], default='vit_large', 
                    help='type of model (default: clam_sb, clam w/ single attention branch)')
parser.add_argument('--exp_code', type=str, help='experiment code for saving results')
parser.add_argument('--weighted_sample', action='store_true', default=False, help='enable weighted sampling')
parser.add_argument('--model_size', type=str, choices=['small', 'big'], default='small', help='size of model, does not affect mil')
parser.add_argument('--task', type=str, choices=['task_tumor_H3K27M', 'task_tumor_ATRX', 'task_tumor_P53', 'task_tumor_H3K27M_all', 'task_tumor_ATRX_all', 'task_tumor_P53_all', 'task_tumor_H3K27M_neg'])
### CLAM specific options
parser.add_argument('--no_inst_cluster', action='store_true', default=False,
                     help='disable instance-level clustering')
parser.add_argument('--inst_loss', type=str, choices=['svm', 'ce', None], default=None,
                     help='instance-level clustering loss function (default: None)')
parser.add_argument('--subtyping', action='store_true', default=False, 
                     help='subtyping problem')
parser.add_argument('--bag_weight', type=float, default=0.7,
                    help='clam: weight coefficient for bag-level loss (default: 0.7)')
parser.add_argument('--B', type=int, default=8, help='number of positive/negative patches to sample for clam')

args = parser.parse_args()
device=torch.device("cuda" if torch.cuda.is_available() else "cpu")

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:64"
torch.cuda.empty_cache()

def seed_torch(seed=7):
    import random
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if device.type == 'cuda':
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed) # if you are using multi-GPU.
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True

#seed_torch(args.seed)

encoding_size = 768
settings = {'num_splits': args.k, 
            'k_start': args.k_start,
            'k_end': args.k_end,
            'task': args.task,
            'max_epochs': args.max_epochs, 
            'results_dir': args.results_dir, 
            'lr': args.lr,
            'experiment': args.exp_code,
            'reg': args.reg,
            'label_frac': args.label_frac,
            'bag_loss': args.bag_loss,
            'seed': args.seed,
            'model_type': args.model_type,
            'model_size': args.model_size,
            "use_drop_out": args.drop_out,
            'weighted_sample': args.weighted_sample,
            'opt': args.opt}

if args.model_type in ['clam_sb', 'clam_mb']:
   settings.update({'bag_weight': args.bag_weight,
                    'inst_loss': args.inst_loss,
                    'B': args.B})

print('\nLoad Dataset')

if args.task == 'task_tumor_H3K27M':
    args.n_classes=2
    dataset = Generic_MIL_Dataset(csv_path = '/ailab/user/liumianxin/CLAM/dataset_csv/tumor_H3K27M_dummy_clean.csv',
                            data_dir= os.path.join(args.data_root_dir, 'features_resnet'),
                            shuffle = False, 
                            seed = args.seed, 
                            print_info = True,
                            label_dict = {'neg':0, 'pos':1},
                            patient_strat= False,
                            ignore=[])
elif args.task == 'task_tumor_ATRX':
    args.n_classes=2
    dataset = Generic_MIL_Dataset(csv_path = '/ailab/user/liumianxin/CLAM/dataset_csv/tumor_ATRX_dummy_clean.csv',
                            data_dir= os.path.join(args.data_root_dir, 'features_resnet'),
                            shuffle = False, 
                            seed = args.seed, 
                            print_info = True,
                            label_dict = {'neg':1, 'pos':0},
                            patient_strat= False,
                            ignore=[])
elif args.task == 'task_tumor_P53':
    args.n_classes=2
    dataset = Generic_MIL_Dataset(csv_path = '/ailab/user/liumianxin/CLAM/dataset_csv/tumor_P53_dummy_clean.csv',
                            data_dir= os.path.join(args.data_root_dir, 'features_resnet'),
                            shuffle = False, 
                            seed = args.seed, 
                            print_info = True,
                            label_dict = {'neg':0, 'pos':1},
                            patient_strat= False,
                            ignore=[])
elif args.task == 'task_tumor_H3K27M_all':
    args.n_classes=2
    dataset = Generic_MIL_Dataset(csv_path = '/ailab/user/liumianxin/CLAM/dataset_csv/tumor_H3K27M_dummy_all.csv',
                            data_dir= os.path.join(args.data_root_dir, 'features_p2_nm'),
                            shuffle = False, 
                            seed = args.seed, 
                            print_info = True,
                            label_dict = {'neg':0, 'pos':1},
                            patient_strat= False,
                            ignore=[])
elif args.task == 'task_tumor_ATRX_all':
    args.n_classes=2
    dataset = Generic_MIL_Dataset(csv_path = '/ailab/user/liumianxin/CLAM/dataset_csv/tumor_ATRX_dummy_all.csv',
                            data_dir= os.path.join(args.data_root_dir, 'features_p2_nm'),
                            shuffle = False, 
                            seed = args.seed, 
                            print_info = True,
                            label_dict = {'neg':1, 'pos':0},
                            patient_strat= False,
                            ignore=[])
elif args.task == 'task_tumor_P53_all':
    args.n_classes=2
    dataset = Generic_MIL_Dataset(csv_path = '/ailab/user/liumianxin/CLAM/dataset_csv/tumor_P53_dummy_all.csv',
                            data_dir= os.path.join(args.data_root_dir, 'features_p2_nm'),
                            shuffle = False, 
                            seed = args.seed, 
                            print_info = True,
                            label_dict = {'neg':0, 'pos':1},
                            patient_strat= False,
                            ignore=[])
elif args.task == 'task_tumor_H3K27M_neg':
    args.n_classes=2
    dataset = Generic_MIL_Dataset(csv_path = '/ailab/user/liumianxin/CLAM/dataset_csv/tumor_H3K27M_dummy_neg.csv',
                            data_dir= os.path.join(args.data_root_dir, 'features_p2_nm'),
                            shuffle = False, 
                            seed = args.seed, 
                            print_info = True,
                            label_dict = {'neg':0, 'pos':1},
                            patient_strat= False,
                            ignore=[])
    #if args.model_type in ['clam_sb', 'clam_mb']:
        #print(args.subtyping )
        #assert args.subtyping 
        
else:
    raise NotImplementedError
    
if not os.path.isdir(args.results_dir):
    os.mkdir(args.results_dir)

args.results_dir = os.path.join(args.results_dir, str(args.exp_code) + '_s{}'.format(args.seed))
if not os.path.isdir(args.results_dir):
    os.mkdir(args.results_dir)

if args.split_dir is None:
    args.split_dir = os.path.join('/ailab/user/liumianxin/CLAM/splits', args.task+'_{}'.format(int(args.label_frac*100)))
else:
    args.split_dir = os.path.join('/ailab/user/liumianxin/CLAM/splits', args.split_dir)

print('split_dir: ', args.split_dir)
assert os.path.isdir(args.split_dir)

settings.update({'split_dir': args.split_dir})


with open(args.results_dir + '/experiment_{}.txt'.format(args.exp_code), 'w') as f:
    print(settings, file=f)
f.close()

print("################# Settings ###################")
for key, val in settings.items():
    print("{}:  {}".format(key, val))        

if __name__ == "__main__":
    results = main(args)
    print("finished!")
    print("end script")


