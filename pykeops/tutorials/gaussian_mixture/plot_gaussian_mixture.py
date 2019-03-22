"""
Fitting a Gaussian Mixture Model
=====================================

In this tutorial, we show how to use KeOps to fit
a Gaussian Mixture Model with a **custom sparsity prior**
through **gradient descent** on the empiric log-likelihood.
"""

####################################################################
# Setup
# -----------
# 
# Standard imports:

import numpy as np

from matplotlib import pyplot as plt
import matplotlib.cm as cm

import torch
from torch.nn import Module, Parameter
from torch.nn.functional import softmax, log_softmax

from pykeops.torch import Kernel, kernel_product


####################################################################
# Define our dataset: a spiral in the unit square.

# Choose the storage place for our data : CPU (host) or GPU (device) memory.
dtype = torch.cuda.FloatTensor if torch.cuda.is_available() else torch.FloatTensor

N = 10000  # Number of samples
t = torch.linspace(0, 2 * np.pi, N + 1)[:-1]
x = torch.stack((.5 + .4 * (t / 7) * t.cos(), .5 + .3 * t.sin()), 1)
x = x + .02 * torch.randn(x.shape)
x = x.type(dtype)
x.requires_grad = True

####################################################################
# Display:

# Create a uniform grid on the unit square:
res = 200
ticks = np.linspace(0, 1, res + 1)[:-1] + .5 / res
X, Y = np.meshgrid(ticks, ticks)

grid = torch.from_numpy(np.vstack((X.ravel(), Y.ravel())).T).contiguous().type(dtype)


####################################################################
# Gaussian Mixture Model
# ----------------------
#
# In this tutorial, we focus on a Gaussian Mixture Model
# with varying covariance matrices. For all class indices :math:`j`
# in :math:`[0,M)`, we denote by 
#

class GaussianMixture(Module):
    def __init__(self, M, sparsity=0, D=2):
        super(GaussianMixture, self).__init__()
        
        # Let's use a mixture of Gaussian kernels, i.e.
        #        k(x_i,y_j) = exp( - WeightedSquaredNorm(gamma, x_i-y_j ) )
        self.params = {'id': Kernel('gaussian(x,y)')}
        self.mu = Parameter(torch.rand(M, D).type(dtype))
        self.A = 10 * torch.ones(M, 1, 1) * torch.eye(D, D).view(1, D, D)
        self.A = Parameter((self.A).type(dtype).contiguous())
        self.w = Parameter(torch.ones(M, 1).type(dtype))
        self.sparsity = sparsity
    
    
    def update_covariances(self):
        """Computes the full covariance matrices from the model's parameters."""
        (M, D, _) = self.A.shape
        self.params['gamma'] = (torch.matmul(self.A, self.A.transpose(1, 2))).view(M, D * D)
    
    
    def covariances_determinants(self):
        """Computes the determinants of the covariance matrices.
        
        N.B.: PyTorch still doesn't support batched determinants, so we have to
              implement this formula by hand.
        """
        S = self.params['gamma']
        if S.shape[1] == 2 * 2:
            dets = S[:, 0] * S[:, 3] - S[:, 1] * S[:, 2]
        else:
            raise NotImplementedError
        return dets.view(-1, 1)
    
    
    def weights(self):
        """Scalar factor in front of the exponential, in the density formula."""
        return softmax(self.w, 0) * self.covariances_determinants().sqrt()
    
    
    def weights_log(self):
        """Logarithm of the scalar factor, in front of the exponential."""
        return log_softmax(self.w, 0) + .5 * self.covariances_determinants().log()
    
    
    def likelihoods(self, sample):
        """Samples the density on a given point cloud."""
        self.update_covariances()
        return kernel_product(self.params, sample, self.mu, self.weights(), mode='sum')
    
    
    def log_likelihoods(self, sample):
        """Log-density, sampled on a given point cloud."""
        self.update_covariances()
        return kernel_product(self.params, sample, self.mu, self.weights_log(), mode='lse')
    
    
    def neglog_likelihood(self, sample):
        """Returns -log(likelihood(sample)) up to an additive factor."""
        ll = self.log_likelihoods(sample)
        log_likelihood = torch.mean(ll)
        # N.B.: We add a custom sparsity prior, which promotes empty clusters
        #       through a soft, concave penalization on the class weights.
        return -log_likelihood + self.sparsity * softmax(self.w, 0).sqrt().mean()
    
    
    def get_sample(self, N):
        """Generates a sample of N points."""
        raise NotImplementedError()
    
    
    def plot(self, sample):
        """Displays the model."""
        plt.clf()
        # Heatmap:
        heatmap = self.likelihoods(grid)
        heatmap = heatmap.view(res, res).data.cpu().numpy()  # reshape as a "background" image
        
        scale = np.amax(np.abs(heatmap[:]))
        plt.imshow(-heatmap, interpolation='bilinear', origin='lower',
                   vmin=-scale, vmax=scale, cmap=cm.RdBu,
                   extent=(0, 1, 0, 1))
        
        # Log-contours:
        log_heatmap = self.log_likelihoods(grid)
        log_heatmap = log_heatmap.view(res, res).data.cpu().numpy()
        
        scale = np.amax(np.abs(log_heatmap[:]))
        levels = np.linspace(-scale, scale, 41)
        
        plt.contour(log_heatmap, origin='lower', linewidths=1., colors="#C8A1A1",
                    levels=levels, extent=(0, 1, 0, 1))
        
        # Scatter plot of the dataset:
        xy = sample.data.cpu().numpy()
        plt.scatter(xy[:, 0], xy[:, 1], 100 / len(xy), color='k')


####################################################################
# Optimization 
# ------------
#
# In typical :mod:`torch` fashion, we fit our Mixture Model
# to the data through a stochastic gradient descent on the empiric log-likelihood:


model = GaussianMixture(30, sparsity=20)
optimizer = torch.optim.Adam(model.parameters(), lr=.1)

loss = np.zeros(501)

for it in range(501):
    optimizer.zero_grad()  # Reset the gradients (PyTorch syntax...).
    cost = model.neglog_likelihood(x)  # Cost to minimize.
    cost.backward()  # Backpropagate to compute the gradient.
    optimizer.step()
    
    loss[it] = cost.data.cpu().numpy()
    
    # sphinx_gallery_thumbnail_number = 6
    if it in [0, 10, 100, 150, 250, 500]:
        plt.pause(.01)
        plt.figure()
        model.plot(x)
        plt.title('Density, iteration ' + str(it), fontsize=20)
        plt.pause(.01)



####################################################################
# Monitor the optimization process:
#
plt.figure()
plt.plot(loss)

