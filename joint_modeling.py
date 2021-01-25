import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import torch
import gpytorch
import irregular_multitask
import transformer

import data_collection
import read_exp
import single_task

def main():
    scan_df = data_collection.get_exp_data(True)
    with gpytorch.settings.max_cg_iterations(2000):
        param_names, m, lk, tx, ty = joint_model(train = True)
        m_sim, lk_sim = sim_model(tx, ty, param_names)
        
        
    m.eval()
    lk.eval()

    m_sim.eval()
    lk_sim.eval()
    
    print(scan_df[param_names])
    
    scan_x = scan_df[param_names].to_numpy()
    scan_x_norm = torch.from_numpy(tx.forward(scan_x)).float()
    scan_y = scan_df['stats_XRMS'].to_numpy()

        
    scan_i = torch.full_like(scan_x_norm, dtype = torch.long, fill_value = 1)
    scan_i_sim = torch.full_like(scan_x_norm, dtype = torch.long, fill_value = 0)

    with torch.no_grad(), gpytorch.settings.fast_pred_var():
        pred = lk(m(scan_x_norm.cuda(),scan_i.cuda()))
        pred_sim = lk(m(scan_x_norm.cuda(), scan_i_sim.cuda()))

        pred_sim_single = lk_sim(m_sim(scan_x_norm.cuda()))

    fig,ax = plt.subplots()
    ax.plot(scan_x[:,2], scan_y, 'C0+', label = 'exp data')

    ax.set_xlabel(param_names[2])
    ax.set_ylabel('XRMS')
    
    ps = [pred, pred_sim, pred_sim_single]
    ls = ['exp','sim','sim_single']
    cs = ['C1','C2', 'C3']
    
    for p,l,c in zip(ps, ls, cs):
        pred = p
        lower, upper = p.confidence_region()
        mean = p.mean.cpu()
        lower = lower.cpu()
        upper = upper.cpu()    
    
        mean = ty.backward(mean.detach().numpy().reshape(-1,1)).flatten()
        lower = ty.backward(lower.detach().numpy().reshape(-1,1)).flatten()
        upper = ty.backward(upper.detach().numpy().reshape(-1,1)).flatten()

        
        ax.plot(scan_x[:,2], mean, '-', c = c, label = l)
        ax.fill_between(scan_x[:,2], lower, upper, alpha = 0.25, lw=0, fc = c)

    ax.legend()

def sim_model(tx, ty, param_names):
    sim_x_df, sim_y_df = data_collection.get_sim_data()

    sim_pts = 12000
    sim_x = sim_x_df[param_names][-sim_pts:].to_numpy()
    sim_y = sim_y_df['end_sigma_x'][-sim_pts:].to_numpy().reshape(-1,1)

    #transform
    sim_x = tx.forward(sim_x)
    sim_y = ty.forward(sim_y)
    
    sim_x = torch.from_numpy(sim_x).float()
    sim_y = torch.from_numpy(sim_y).float().flatten()

    likelihood = gpytorch.likelihoods.GaussianLikelihood()
    model = single_task.ExactGPModel(sim_x,
                                     sim_y,
                                     likelihood,
                                     ard_num_dims = 6)
    sim_x = sim_x.cuda()
    sim_y = sim_y.cuda()
    model = model.cuda()
    likelihood = likelihood.cuda()

    single_task.train_model(model, likelihood, sim_x, sim_y, iter_steps = 600)
    
    return model, likelihood
    
    
def joint_model(train = True):
    sim_x_df, sim_y_df = data_collection.get_sim_data()
    exp_df = data_collection.get_exp_data()

    #print(sim_df)
    #print(exp_df)

    param_names = sim_x_df.keys()

    print(sim_x_df)
    sim_pts = 8000
    
    #access the input param columns based on param_names
    exp_x = torch.from_numpy(exp_df[param_names].to_numpy()).float()
    sim_x = torch.from_numpy(sim_x_df[param_names][-sim_pts:].to_numpy()).float()

    exp_y = torch.from_numpy(exp_df['stats_XRMS'].to_numpy()).float().flatten()
    sim_y = torch.from_numpy(sim_y_df['end_sigma_x'][-sim_pts:].to_numpy()).float().flatten()

    likelihood = gpytorch.likelihoods.GaussianLikelihood()

    sim_i = torch.full_like(sim_x, dtype = torch.long, fill_value = 0)
    exp_i = torch.full_like(exp_x, dtype = torch.long, fill_value = 1)

    full_x = torch.cat([sim_x, exp_x])
    full_i = torch.cat([sim_i, exp_i])
    full_y = torch.cat([sim_y, exp_y])

    tx = transformer.Transformer(full_x.numpy())
    ty = transformer.Transformer(full_y.numpy().reshape(-1,1), 'standardize')

    full_x = torch.from_numpy(tx.forward(full_x.numpy()))
    full_y = torch.from_numpy(ty.forward(full_y.numpy().reshape(-1,1))).flatten()
    

    
    
    model = irregular_multitask.MultitaskGPModel((full_x, full_i),
                                                 full_y,
                                                 likelihood,
                                                 ard_num_dims = 6)
    
    
    full_x = full_x.cuda()
    full_i = full_i.cuda()
    full_y = full_y.cuda()
    model = model.cuda()
    likelihood = likelihood.cuda()

    if train:
        irregular_multitask.train_model(model, likelihood, full_x, full_y, full_i, iter_steps = 600)

    #print task cov matrix
    cov_fac = model.task_covar_module.covar_factor.data
    cov_var = torch.exp(model.task_covar_module.raw_var.data)
    kij = torch.matmul(cov_fac,torch.transpose(cov_fac,0,1)) + torch.diag(cov_var)
    print(kij)
    print(model.covar_module.lengthscale)

    return param_names, model, likelihood, tx, ty
    
    
main()
plt.show()
