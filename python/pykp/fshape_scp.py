import numpy as np
import ctypes
from ctypes import *
import os.path

# extract cuda_fshape_scp function pointer in the shared object cuda_fshape_scp_*.so
def get_cuda_fshape_scp(name_geom , name_sig , name_var):
    """
    Loads the routine from the compiled .so file.
    """
    name = name_geom + name_sig + name_var
    print(name)
    dll_name = "cuda_fshape_scp_" + name + ".so"

    dllabspath = os.path.dirname(os.path.abspath(__file__)) + os.path.sep+ 'build' + os.path.sep + dll_name
    dll = ctypes.CDLL(dllabspath, mode=ctypes.RTLD_GLOBAL)
    func = dll.cudafshape
    # Arguments :     1/sx^2,   1/sf^2, 1/st^2,     x,               y,                f,                  g,              alpha,            beta,             result,           dim-xy, dim-fg,  dim-beta, nx,   ny
    func.argtypes = [c_float, c_float, c_float, POINTER(c_float), POINTER(c_float), POINTER(c_float), POINTER(c_float), POINTER(c_float), POINTER(c_float), POINTER(c_float), c_int, c_int,   c_int,     c_int, c_int]
    return func

# convenient python wrapper for __cuda_fshape_scp it does all job with types convertation from python ones to C++ ones 
def cuda_shape_scp(x, y, f, g, alpha, beta, result, sigma_geom, sigma_sig, sigma_var = 1, kernel_geom = "gaussian", kernel_sig ="gaussian", kernel_var = "binet"):
    """
    Implements the operation :

    (x_i, y_j,f_i, g_j, alpha_i, beta_j)  ->  ( \sum_j kgeom(x_i,y_j) ksig(f_i,g_j) kvar(alpha_i,beta_j) )_i ,

    where kgeom, ksig, kvar are kernels function of parameter "sigmageom", "sigmasig", "sigmavar".

    NB : this function is useful to compute varifold like distance between shapes.
    """
    # From python to C float pointers and int :
    x_p      =  x.ctypes.data_as(POINTER(c_float))
    y_p      =  y.ctypes.data_as(POINTER(c_float))
    f_p      =  f.ctypes.data_as(POINTER(c_float))
    g_p      =  g.ctypes.data_as(POINTER(c_float))
    alpha_p  =  alpha.ctypes.data_as(POINTER(c_float))
    beta_p   =  beta.ctypes.data_as(POINTER(c_float))
    result_p =  result.ctypes.data_as(POINTER(c_float))

    nx = x.shape[0] ; ny = y.shape[0]

    dimPoint = x.shape[1]
    dimSig   = f.shape[1]
    dimVect  = beta.shape[1]

    print(dimPoint)
    print(dimSig)
    print(dimVect)
    
    ooSigma_geom2 = float(1/ (sigma_geom*sigma_geom)) # Compute this once and for all
    ooSigma_sig2  = float(1 / (sigma_sig*sigma_sig)) # Compute this once and for all
    ooSigma_var2  = float(1 / (sigma_var*sigma_var)) # Compute this once and for all

    # create __cuda_fshape_scp function with get_cuda_fshape_scp()
    __cuda_fshape_scp = get_cuda_fshape_scp(kernel_geom , kernel_sig , kernel_var)
    # Let's use our GPU, which works "in place" :
    __cuda_fshape_scp(ooSigma_geom2,ooSigma_sig2,ooSigma_var2, x_p, y_p, f_p, g_p, alpha_p, beta_p, result_p, dimPoint,dimSig, dimVect, nx, ny )



if __name__ == '__main__':
    """
    testing the cuda kernel with a python  implementation
    """
    np.set_printoptions(linewidth=200)

    sizeX    = int(40)
    sizeY    = int(15)
    dimPoint = int(3)
    dimSig = int(1)
    dimVect  = int(3)
    sigma_geom  = 1.0
    sigma_sig  = 1.0
    sigma_var   = np.pi/2

    def gaussian(r2,s):
        return np.exp(-r2/(s*s))

    def cauchy(r2,s):
        return 1 /(1 + r2/(s*s))

    def binet(prs):
        return prs**2

    def linear(prs):
        return prs

    def gaussian_unoriented(prs,s):
        return np.exp( (-2.0 + 2.0 * prs*prs) / (s*s))

    def gaussian_oriented(prs,s):
        return np.exp( (-2.0 + 2.0 * prs) / (s*s))

    def squdistance_matrix(ax,by):
        return np.sum( (ax[:,np.newaxis,:] - by[np.newaxis,:,:]) **2, axis=2)    

    if True:
        x     = np.random.rand(sizeX,dimPoint).astype('float32')
        y     = np.random.rand(sizeY,dimPoint).astype('float32')
        f     = np.random.rand(sizeX,dimSig).astype('float32')
        g     = np.random.rand(sizeY,dimSig).astype('float32')
        alpha = np.random.rand(sizeX,dimVect ).astype('float32')
        beta  = np.random.rand(sizeY,dimVect ).astype('float32')
    else :
        x     =(np.linspace(0.5,2,sizeX)[:,np.newaxis] * np.linspace(0,3,dimPoint)[np.newaxis,:] ).astype('float32')
        print(x)
        alpha =(np.linspace(-1.1,2,sizeX)[:,np.newaxis] * np.linspace(1,1,dimPoint)[np.newaxis,:]).astype('float32')
        print(alpha)
        f     =-(np.linspace(1,2,sizeX)[:,np.newaxis] ).astype('float32')
        print(f)
        y     =-(np.linspace(1,3,sizeY)[:,np.newaxis] * np.linspace(-1,1,dimPoint)[np.newaxis,:] ).astype('float32')
        print(y)
        beta  =-(np.linspace(1,2,sizeY)[:,np.newaxis] * np.linspace(1,2,dimPoint)[np.newaxis,:]).astype('float32')
        g     =(np.linspace(1,2,sizeY)[:,np.newaxis] ).astype('float32')
    
    # Call cuda kernel
    gamma = np.zeros(sizeX).astype('float32')
    cuda_shape_scp(x, y, f, g, alpha, beta, gamma, sigma_geom, sigma_sig, sigma_var,"cauchy","gaussian", "gaussian_oriented")

    
    # Python version
    areaa = np.linalg.norm(alpha,axis=1)
    areab = np.linalg.norm(beta,axis=1)

    nalpha = alpha / areaa[:,np.newaxis]
    nbeta = beta / areab[:,np.newaxis]
    
    gamma_py = np.sum( (areaa[:,np.newaxis] * areab[np.newaxis,:]) *  cauchy(squdistance_matrix(x,y),sigma_geom) *  gaussian(squdistance_matrix(f,g),sigma_sig) * gaussian_oriented(nalpha @ nbeta.T,sigma_var), axis=1 )

    # compare output
    print("\nFshape distance cuda:")
    print(gamma)

    print("\nFshape distance numpy:")
    print(gamma_py)

    print("\nIs everything okay ? ")
    print(np.allclose(gamma, gamma_py ))
