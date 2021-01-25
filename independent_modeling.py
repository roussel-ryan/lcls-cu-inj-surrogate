import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import torch
import gpytorch
import transformer

#import data_collection
import get_experiment_data as ged
import get_simulation_data as gsd
import single_task


def main():
    raw_exp, raw_sim = get_datasets()
    
    data_pkt = combine_datasets()

    tx = data_pkt[2]
    ty = data_pkt[3]
    
    sim_model, sim_lk = create_independent_model(data_pkt,'sim', iters = 75, lr = 0.1, load_path = 'sim_model.pth')
    exp_model, exp_lk = create_independent_model(data_pkt,'exp', iters = 100, lr = 0.1, load_path = 'exp_model.pth')

    torch.save(sim_model.state_dict(),'sim_model.pth')
    torch.save(exp_model.state_dict(),'exp_model.pth')
    
    #get single scan exp data
    print(raw_exp['scan_number'].describe())
    scan_idx = 0
    indicies = raw_exp.index[raw_exp['scan_number'] == scan_idx]
    scan_x = data_pkt[0].iloc[indicies].sort_values('SOLN:IN20:121:BDES', axis=0)
    scan_y = data_pkt[1].iloc[scan_x.index]

    scan_x_torch = torch.from_numpy(tx.forward(scan_x.loc[:,scan_x.columns != 'type'].to_numpy(dtype = np.float32)))

    
    fig,ax = plt.subplots()
    add_gp(exp_model, exp_lk,
           scan_x_torch, 4,
           data_pkt[2], data_pkt[3], ax)

    add_gp(sim_model, sim_lk,
           scan_x_torch, 4,
           data_pkt[2], data_pkt[3], ax)

    ax.plot(scan_x['SOLN:IN20:121:BDES'],scan_y['stats_XRMS'],'+')
    

def add_gp(m, lk, x, col, tx, ty, ax, c = 'C0', lbl = ''):
    m.eval()
    lk.eval()
    
    with torch.no_grad():
        m = m.cuda()
        lk = lk.cuda()
        pred = lk(m(x.cuda()))

    lower, upper = pred.confidence_region()
    mean = pred.mean.cpu()
    lower = lower.cpu()
    upper = upper.cpu()

    mean = ty.backward(mean.detach().numpy().reshape(-1,1)).flatten()
    lower = ty.backward(lower.detach().numpy().reshape(-1,1)).flatten()
    upper = ty.backward(upper.detach().numpy().reshape(-1,1)).flatten()

    x = tx.backward(x.numpy())
        
    ax.plot(x[:,col], mean, '-', c = c, label = lbl)
    ax.fill_between(x[:,col], lower, upper, alpha = 0.25, lw=0, fc = c)

    
    
def create_independent_model(data, mtype, iters = 600, lr = 0.01, load_path = None):
    x = data[0]
    y = data[1]
    tx = data[2]
    ty = data[3]

    print(x)
    
    #get data of mtype
    x = x.loc[x['type'] == mtype, x.columns != 'type'].to_numpy(dtype = np.float32)
    x = tx.forward(x)

    y = y.loc[y['type'] == mtype, y.columns != 'type'].to_numpy(dtype = np.float32)
    y = ty.forward(y)

    print(x.shape)
    print(y.shape)
    
    #convert to torch
    x = torch.from_numpy(x)
    y = torch.from_numpy(y)[:,0].flatten()
    
    #create and train model
    likelihood = gpytorch.likelihoods.GaussianLikelihood()
    model = single_task.ExactGPModel(x,
                                     y,
                                     likelihood,
                                     ard_num_dims = 6)

    if load_path == None:

        x = x.cuda()
        y = y.cuda()
        model = model.cuda()
        likelihood = likelihood.cuda()

        single_task.train_model(model, likelihood, x, y, iter_steps = iters, lr = lr)
        print(model.covar_module.base_kernel.lengthscale)
    else:
        state_dict = torch.load(load_path)
        model.load_state_dict(state_dict)
        
    return model, likelihood


    
def combine_datasets():
    '''create independent models of the experiment and simulated data'''
    exp,sim = get_datasets()

    #get independent variables
    x_names = [name for name in exp.keys() if ':' in name and 'EGU' not in name]
    y_names = [name for name in exp.keys() if 'stats' in name]
    
    x_dfs = []
    y_dfs = []
    frames = [exp,sim]
    types = ['exp','sim']

    for i in range(2):
        temp_x = frames[i][x_names]
        temp_x['type'] = types[i]

        temp_y = frames[i][y_names]
        temp_y['type'] = types[i]

        x_dfs += [pd.DataFrame(temp_x)]
        y_dfs += [pd.DataFrame(temp_y)]
        
    x_df = pd.concat(x_dfs)
    y_df = pd.concat(y_dfs)


    #get normalization
    tx = transformer.Transformer(x_df.loc[:, x_df.columns != 'type'].to_numpy(dtype = np.float))
    ty = transformer.Transformer(y_df.loc[:, y_df.columns != 'type'].to_numpy(dtype = np.float),'standardize')

    return x_df, y_df, tx, ty

    
def get_datasets():
    exp = ged.get_solenoid_scan_data()
    sim = gsd.get_sim_data()

    #remove ACCL:IN20:400:L0B_PDES from data and replace with the pulse length distgen:t_dist:length:value
    #pulse length estimated to be 4 ps (from Nicole)
    exp = exp.drop(labels = 'ACCL:IN20:400:L0B_PDES',axis = 1)
    exp['distgen:t_dist:length:value'] = 4.0

    
    #rename objective columns in sim data
    obj_names_key = {'end_sigma_x':'stats_XRMS', 'end_sigma_y':'stats_YRMS'}
    sim = sim.rename(columns = obj_names_key)

    #scale sim ouputs
    for name in obj_names_key.items():
        sim[name[1]] = 1e6 * np.asfarray(sim[name[1]])
    
    return exp,sim

main()
plt.show()
