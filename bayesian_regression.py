# -*- coding: utf-8 -*-

import numpy as np
from scipy.stats import multivariate_normal as mvn


class BayesianRegression(object):
    '''
    Bayesian Regression with type maximum likelihood for determining point estimates
    for precision variables alpha and beta, where alpha is precision of prior of weights
    and beta is precision of likelihood
    
    Parameters:
    -----------
    
    X: numpy array of size 'n x m'
       Matrix of explanatory variables (should not include bias term)
       
    Y: numpy arra of size 'n x 1'
       Vector of dependent variables (we assume)
       
    thresh: float
       Threshold for convergence for alpha (precision of prior)
       
    '''
    
    def __init__(self,X,Y, thresh = 1e-5):
        
        # center input data for simplicity of further computations
        self.X,self.mu_X       =  self._center(X)
        self.Y,self.mu_Y       =  self._center(Y)
        self.thresh            =  thresh
        
        # to speed all further computations save svd decomposition and reuse it later
        self.u,self.d,self.v   =  np.linalg.svd(self.X, full_matrices = False)
        
        # precision parameters, they are calculated during evidence approximation
        self.alpha             = 0 
        self.beta              = 0
        
        # mean and precision of posterior distribution of weights
        self.w_mu              = 0
        self.w_beta            = 0
        
    @staticmethod
    def _center(x):
        '''
        Centers data by removing mean, this simplifies further computation
        '''
        if len(x.shape) > 1:
            mu     = np.mean(x, axis = 0)
            return [x - mu,mu]
        else:
            mu     = np.mean(x)
            return [x - np.mean(x),mu]



    def _weights_posterior_params(self,alpha,beta):
        '''
        Calculates parameters of posterior distribution of weights after data was 
        observed. Uses svd for fast calculaltions.
        
        # Small Theory note:
        ---------------------
        Multiplying likelihood of data on prior of weights we obtain distribution 
        proportional to posterior of weights. By completing square in exponent it 
        is easy to prove that posterior distribution is Gaussian.
        
        Parameters:
        -----------
        
        alpha: float
            Precision parameter for prior distribution of weights
            
        beta: float
            Precision parameter for noise distribution
            
        Returns:
        --------
        
        : list of two numpy arrays
           First element of list is mean and second is precision of multivariate 
           Gaussian distribution
           
        '''
        precision             = beta*np.dot(self.X.T,self.X)+alpha
        self.diag             = self.d/(self.d**2 + alpha/beta)
        p1                    = np.dot(self.v.T,np.diag(self.diag))
        p2                    = np.dot(self.u.T,self.Y)
        w_mu                  = np.dot(p1,p2)
        return [w_mu,precision]
        
        
    def _pred_dist_params(self,alpha,beta,x,w_mu,w_precision):
        '''
        Calculates parameters of predictive distribution
        
        Parameters:
        -----------
        
        alpha: float
            Precision parameter for prior distribution of weights
            
        beta: float
            Precision parameter for noise distribution
            
        x: numpy array of size 'unknown x m'
            Set of features for which corresponding responses should be predicted
            
        w_mu: numpy array of size 'm x 1'
            mean of posterior distribution of weights
            
        w_precision: numpy array of size 'm x 1'
            precision of posterior distribution of weights
        
        
        Returns:
        ---------
        
        :list of two numpy arrays (each has size 'unknown x 1')
            Parameters of univariate gaussian distribution [mean and variance] 
        
        '''
        mu_pred      =  np.dot(x,w_mu)
        d            =  1/(self.d**2 + alpha/beta)
        S            =  np.dot( np.dot(self.v.T, np.diag(d) ) , self.v)
        var_pred     =  np.array([(1 + np.dot(u,S.dot(u)))/beta for u in x])
        return [mu_pred,var_pred]

        
    def _evidence_approx(self,max_iter = 100,method = "EM"):
        '''
        Performs evidence approximation , finds precision  parameters that maximize 
        type II likelihood. There are two different fitting algorithms, namely EM
        and fixed-point algorithm, empirical evidence shows that fixed-point algorithm
        is faster than EM
        
        Parameters:
        -----------
        
        max_iter: int
              Maximum number of iterations
        
        method: str
              Can have only two values : "EM" or "fixed-point"
        
        '''
        
        # number of observations and number of paramters in model
        n,m         = np.shape(self.X)
        
        # initial values of alpha and beta 
        alpha, beta = np.random.random(2)
        
        # store log likelihood at each iteration
        log_likes   = []
        
        for i in range(max_iter):
            
            # find mean for posterior of w ( for EM this is E-step)
            d       =  self.d**2
            p1_mu   =  np.dot(self.v.T, np.diag(self.d/(d+alpha/beta)))
            p2_mu   =  np.dot(self.u.T,Y)
            mu      =  np.dot(p1_mu,p2_mu)
            
            if method == "fixed-point":
     
                # update gamma
                gamma   =  np.sum(beta*d/(beta*d + alpha))
               
                # use updated mu and gamma parameters to update alpha and beta
                alpha      =  gamma/np.dot(mu,mu)
                error      =  self.Y - np.dot(self.X,mu)
                beta       =  (n - gamma)/np.dot(error,error)
               
            elif method == "EM":
                
                # M-step, update parameters alpha and beta
                alpha      = m / (np.dot(mu,mu) + np.sum(1/(beta*d+alpha)))
                err        = Y - np.dot(self.X,mu)
                beta       = n / ( np.dot(err,err) + np.sum(d/(beta*d + alpha)))
                
            # calculate log likelihood p(Y | X, alpha, beta) (constants are not included)
            normaliser =  m/2*np.log(alpha) + n/2*np.log(beta) - 1/2*np.sum(np.log(beta*d+alpha))
            log_like   =  normaliser - alpha/2*np.dot(mu,mu) - beta/2*np.dot(error,error)            
            log_likes.append(log_like)
            
            # if change in log-likelihood is smaller than threshold stop iterations
            if i >=1:
                if log_likes[-1] - log_likes[-2] < self.thresh:
                    break
        
        # write alpha* and beta* to instance variables
        self.alpha = alpha
        self.beta  = beta 
                
            
    def fit(self, evidence_approx_method="fixed_point",iterations = 100):
        '''
        Fits Bayesian linear regression
        '''
        # use type II maximum likelihood to find hyperparameters alpha and beta
        self._fixed_point_evidence_approx(max_iter = iterations, method = evidence_approx_method)

        # find parameters of posterior distribution
        self.w_mu, self.w_beta = self._weights_posterior_params(self.alpha,self.beta)
        
            
    def predict(self,X, Y = None):
        # find parameters of predictive distribution
        mu,var = self._pred_dist_params(self.alpha,self.beta,X,self.w_mu,self.w_beta)
        return mu,var
    
    def predict_mean(self,X):
        '''
        Returns mean of predictive distribution
        
        Para
        '''
        
    
if __name__=="__main__":
    X      = np.ones([100,1])
    Y      = np.ones([100,1])
    X[:,0] = np.linspace(1,10,100)
    Y      = 4*X[:,0]+5*np.random.random(100)
    br     = BayesianRegression(X,Y)
    br.fit()
    my,var = br.predict(X)
    
    
    
    
    
    
    