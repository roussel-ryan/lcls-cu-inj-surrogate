import numpy as np
import torch
import gpytorch
import matplotlib.pyplot as plt
import copy

class ExactGPModel(gpytorch.models.ExactGP):
    def __init__(self, train_x, train_y, likelihood, ard_num_dims = 1):
        super(ExactGPModel, self).__init__(train_x, train_y, likelihood)
        self.mean_module = gpytorch.means.ConstantMean()
        self.covar_module = gpytorch.kernels.ScaleKernel(gpytorch.kernels.RBFKernel(ard_num_dims = ard_num_dims))
        
    def forward(self,x):
        mean_x = self.mean_module(x)
        
        # Get input-input covariance
        covar_x = self.covar_module(x)
        
        return gpytorch.distributions.MultivariateNormal(mean_x, covar_x)


    
    
def train_model(model, likelihood, x, y, iter_steps = 50, lr = 0.1):    
    # Find optimal model hyperparameters
    model.train()
    likelihood.train()

    # Use the adam optimizer
    optimizer = torch.optim.Adam(model.parameters(), lr = lr)  # Includes GaussianLikelihood parameters

    # "Loss" for GPs - the marginal log likelihood
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)

    best_loss = 10000
    for i in range(iter_steps):
        optimizer.zero_grad()
        output = model(x)
        loss = -mll(output, y)
        loss.backward()
        if loss.item() < best_loss:
            best_param = copy.deepcopy(model.state_dict())
            best_loss = loss.item()

        print('Iter %d/50 - Loss: %.3f - Best loss %.3f' % (i + 1, loss.item(), best_loss))
            
        optimizer.step()

    #set model params to the best
    model.load_state_dict(best_param)
    
    #test loss
    #output = model(x, s)
    #loss = -mll(output, y)
    #loss.backward()


def plot_model():
    # Set into eval mode
    model.eval()
    likelihood.eval()

    # Initialize plots
    f, (y1_ax, y2_ax) = plt.subplots(1, 2, figsize=(8, 3))

    # Test points every 0.02 in [0,1]
    test_x = torch.linspace(0, 1, 51)
    tast_i_task1 = torch.full_like(test_x, dtype=torch.long, fill_value=0)
    test_i_task2 = torch.full_like(test_x, dtype=torch.long, fill_value=1)

    # Make predictions - one task at a time
    # We control the task we cae about using the indices

    # The gpytorch.settings.fast_pred_var flag activates LOVE (for fast variances)
    # See https://arxiv.org/abs/1803.06058
    with torch.no_grad(), gpytorch.settings.fast_pred_var():
        observed_pred_y1 = likelihood(model(test_x, tast_i_task1))
        observed_pred_y2 = likelihood(model(test_x, test_i_task2))

    
    # Plot both tasks
    ax_plot(y1_ax, Y1, X1, observed_pred_y1, 'Observed Values (Likelihood)', test_x)
    ax_plot(y2_ax, Y2, X2, observed_pred_y2, 'Observed Values (Likelihood)', test_x)

        
# Define plotting function
def ax_plot(ax, train_y, train_x, rand_var, title, test_x):
    # Get lower and upper confidence bounds
    lower, upper = rand_var.confidence_region()
    # Plot training data as black stars
    ax.plot(train_x.detach().numpy(), train_y.detach().numpy(), 'k*')
    # Predictive mean as blue line
    ax.plot(test_x.detach().numpy(), rand_var.mean.detach().numpy(), 'b')
    # Shade in confidence 
    ax.fill_between(test_x.detach().numpy(), lower.detach().numpy(), upper.detach().numpy(), alpha=0.5)
    ax.set_ylim([-3, 3])
    ax.legend(['Observed Data', 'Mean', 'Confidence'])
    ax.set_title(title)


if __name__ == '__main__':        
    main()
    plt.show()
