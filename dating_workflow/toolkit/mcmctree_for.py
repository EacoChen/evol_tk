import warnings
from glob import glob
from os.path import *

import pandas as pd
from ete3 import Tree
import arviz as az

def cal_ESS(df,burn_in=2000):
    """
    generate effective sample size (ESS) of given dataframe.
    The method 'identity' is the most similar method to the ESS generated by BEAST.

    Args:
        df (pd.DataFrame): [description]
        burn_in (int, optional): [description]. Defaults to 2000.
    """
    col2ESS = {}
    for colname,col in df.iteritems():
        vals = col.values[burn_in:]
        col2ESS[colname] = az.ess(vals,method='identity')
    return col2ESS

def cal_HPD_CI(df,burn_in=2000):
    """
    get HPD CI through mcmc.txt directly instead of reading the log/out file.
    Only calculate high density probility 95%. 
    Args:
        df (pd.DataFrame): [description]
        burn_in (int, optional): [description]. Defaults to 2000.
    """
    col2CI = {}
    for colname,col in df.iteritems():
        vals = col.values[burn_in:]
        col2CI[colname] = az.hdi(vals,hdi_prob=.95)
    return col2CI

def get_posterior_df(mcmc,burn_in=2000,scale=1):
    mcmc_df = pd.read_csv(mcmc, sep='\t', index_col=0)
    if pd.isna(mcmc_df.iloc[-1,-1]):
        mcmc_df = mcmc_df.drop(mcmc_df.index[-1])


    node_names = [_ for _ in mcmc_df.columns if _.startswith('t_n')]
    post_df = pd.DataFrame(columns=['Posterior mean time (100 Ma)',
                                  'CI_width','CIs'],
                          index=node_names + ['lnL'])
    
    raw_n2CI = cal_HPD_CI(mcmc_df,burn_in=burn_in)
    post_df.loc['lnL',:] = [mcmc_df.loc[:,'lnL'].mean(),
                            f"{round(raw_n2CI['lnL'][0],2)} - {round(raw_n2CI['lnL'][1],2)}",
                            round(raw_n2CI['lnL'][1]-raw_n2CI['lnL'][0] ,2),
                            ]
    
    n2CI = {k: f"{round(v[0]*scale,2)} - {round(v[1]*scale,2)}" for k,v in raw_n2CI.items()}
    n2mean_time = {k:round(v*scale,2) for k,v in mcmc_df.mean().to_dict().items()}
    
    post_df.loc[node_names,'Posterior mean time (100 Ma)'] = [n2mean_time[_] for _ in post_df.index if _ !='lnL']
    post_df.loc[node_names,'CIs'] = [n2CI[_] for _ in post_df.index if _ !='lnL']
    post_df.loc[node_names,'CI_width'] = [n2CI[_][1]-n2CI[_][0] for _ in post_df.index if _ !='lnL']    
    return post_df
    
    
def get_node_name_from_log(f):
    # f should be the *.log file
    rows = open(f).read().split('\n')
    idx = [_ for _,r in enumerate(rows) if r == 'Species tree']
    
    idx = idx[0]
    start_idx = idx +3 
    end_idx = 0
    for _ in range(idx,100000):
        if rows[_] == '':
            end_idx = _
            break
    tree_idx1 = end_idx + 1
    tree_idx2 = end_idx + 2
    # find the index
    n2father = {}
    for i in range(start_idx,end_idx):
        row = [_ for _ in rows[i].split(' ') if _]
        father,n,name = row[0],row[1],row[2]
        n2father[name if len(row)==4 else n ] = father
            
    t = Tree(rows[tree_idx2], format=8)
    for l in t.traverse('postorder'):
        if l.up is None:
            break
        if not l.up.name:
            l.up.name = n2father[l.name]
    return t

