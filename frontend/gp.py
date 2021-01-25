import pandas as pd
import torch
import gpytorch
import pickle

import explore
import transformer

from botorch.utils import transforms

torch.cuda.empty_cache()

# We will use the simplest form of GP model, exact inference
class ExactGPModel(gpytorch.models.ExactGP):
    def __init__(self, train_x, train_y, likelihood):
        super(ExactGPModel, self).__init__(train_x, train_y, likelihood)
        self.mean_module = gpytorch.means.ConstantMean()
        self.covar_module = gpytorch.kernels.ScaleKernel(gpytorch.kernels.RBFKernel(ard_num_dims = 6))

    def forward(self, x):
        mean_x = self.mean_module(x)
        covar_x = self.covar_module(x)
        return gpytorch.distributions.MultivariateNormal(mean_x, covar_x)

def train_model(model, likelihood, train_x, train_y, training_iter):
    # Find optimal model hyperparameters
    model.train()
    likelihood.train()

    # Use the adam optimizer
    optimizer = torch.optim.Adam(model.parameters(), lr=0.1)  # Includes GaussianLikelihood parameters

    # "Loss" for GPs - the marginal log likelihood
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)

    for i in range(training_iter):
        # Zero gradients from previous iteration
        optimizer.zero_grad()
        # Output from model
        output = model(train_x)
        # Calc loss and backprop gradients
        loss = -mll(output, train_y)
        loss.backward()
        print(f'Iter {i + 1} - Loss: {loss.item()}   lengthscale: {model.covar_module.base_kernel.lengthscale}   noise: {model.likelihood.noise}')
        optimizer.step()

def main():
    #X, Y = explore.collect_data()

    #X.to_pickle('X.p')
    #Y.to_pickle('Y.p')

    X_df = pd.read_pickle('X.p')
    Y_df = pd.read_pickle('Y.p')

    X = X_df.to_numpy()
    Y = Y_df['end_sigma_z'].to_numpy().reshape(-1,1)

    print(X.shape)
    print(Y.shape)
    
    #transformer for x, y
    tx = transformer.Transformer(X)
    X = tx.forward(X)

    ty = transformer.Transformer(Y, 'standardize')
    Y = ty.forward(Y)
    
    train_x = torch.from_numpy(X).float()
    train_y = torch.from_numpy(Y).float().flatten()

    print(train_x)
    
    
    #ITS GP TIME
    
    # initialize likelihood and model
    likelihood = gpytorch.likelihoods.GaussianLikelihood()
    model = ExactGPModel(train_x, train_y, likelihood)

    train_x = train_x.cuda()
    train_y = train_y.cuda()
    model = model.cuda()
    linkelihood = likelihood.cuda()

    
    train_model(model, likelihood, train_x, train_y, 400)
    
main()
