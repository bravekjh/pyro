from __future__ import absolute_import, division, print_function

from collections import namedtuple

import pytest
import torch
from torch.autograd import Variable

from pyro.contrib.gp.kernels import (Bias, Brownian, Cosine, Exponent, Linear, Matern12, Matern32,
                                     Matern52, Periodic, Polynomial, Product, RationalQuadratic,
                                     SquaredExponential, Sum, VerticalScaling, Warping, WhiteNoise)
from tests.common import assert_equal

T = namedtuple("TestKernelForward", ["kernel", "X", "Z", "K_sum"])

variance = torch.Tensor([3])
lengthscale = torch.Tensor([2, 1, 2])
X = Variable(torch.Tensor([[1, 0, 1], [2, 1, 3]]))
Z = Variable(torch.Tensor([[4, 5, 6], [3, 1, 7], [3, 1, 2]]))

TEST_CASES = [
    T(
        Bias(3, variance),
        X=X, Z=Z, K_sum=18
    ),
    T(
        Brownian(1, variance),
        # only work on 1D input
        X=X[:, 0], Z=Z[:, 0], K_sum=27
    ),
    T(
        Cosine(3, variance, lengthscale),
        X=X, Z=Z, K_sum=-0.193233
    ),
    T(
        Linear(3, variance),
        X=X, Z=Z, K_sum=291
    ),
    T(
        Matern12(3, variance, lengthscale),
        X=X, Z=Z, K_sum=2.685679
    ),
    T(
        Matern32(3, variance, lengthscale),
        X=X, Z=Z, K_sum=3.229314
    ),
    T(
        Matern52(3, variance, lengthscale),
        X=X, Z=Z, K_sum=3.391847
    ),
    T(
        Periodic(3, variance, lengthscale, period=torch.ones(1)),
        X=X, Z=Z, K_sum=18
    ),
    T(
        Polynomial(3, variance, degree=2),
        X=X, Z=Z, K_sum=7017
    ),
    T(
        RationalQuadratic(3, variance, lengthscale, scale_mixture=torch.ones(1)),
        X=X, Z=Z, K_sum=5.684670
    ),
    T(
        SquaredExponential(3, variance, lengthscale),
        X=X, Z=Z, K_sum=3.681117
    ),
    T(
        WhiteNoise(3, variance, lengthscale),
        X=X, Z=Z, K_sum=0
    ),
    T(
        WhiteNoise(3, variance, lengthscale),
        X=X, Z=None, K_sum=6
    )
]

TEST_IDS = [t[0].__class__.__name__ for t in TEST_CASES]


@pytest.mark.parametrize("kernel, X, Z, K_sum", TEST_CASES, ids=TEST_IDS)
def test_kernel_forward(kernel, X, Z, K_sum):
    K = kernel(X, Z)
    assert K.dim() == 2
    assert K.size(0) == 2
    assert K.size(1) == (3 if Z is not None else 2)
    assert_equal(K.sum().item(), K_sum)
    assert_equal(kernel(X).diag(), kernel(X, diag=True))


def test_combination():
    k0 = TEST_CASES[0][0]
    k5 = TEST_CASES[5][0]   # TEST_CASES[1] is Brownian, only work for 1D
    k2 = TEST_CASES[2][0]
    k3 = TEST_CASES[3][0]
    k4 = TEST_CASES[4][0]

    k = Sum(Product(Product(Sum(Sum(k0, k5), k2), 2), k3), Sum(k4, 1))

    K = 2 * (k0(X, Z) + k5(X, Z) + k2(X, Z)) * k3(X, Z) + (k4(X, Z) + 1)

    assert_equal(K.data, k(X, Z).data)

    # test get_subkernel
    assert k.get_subkernel(k5.name) is k5

    # test if error is catched if active_dims are not separated
    k6 = Matern12(2, variance, lengthscale[0], active_dims=[0, 1])
    k7 = Matern32(2, variance, lengthscale[0], active_dims=[1, 2])
    try:
        Sum(k6, k7)
    except ValueError:
        pass
    else:
        raise ValueError("Cannot catch ValueError for kernel combination.")


def test_deriving():
    k = TEST_CASES[6][0]

    def vscaling_fn(x):
        return x.sum(dim=1)

    def iwarping_fn(x):
        return x**2

    owarping_coef = [2, 0, 1, 3, 0]

    K = k(X, Z)
    K_iwarp = k(iwarping_fn(X), iwarping_fn(Z))
    K_owarp = 2 + K ** 2 + 3 * K ** 3
    K_vscale = vscaling_fn(X).unsqueeze(1) * K * vscaling_fn(Z).unsqueeze(0)

    assert_equal(K_iwarp.data, Warping(k, iwarping_fn=iwarping_fn)(X, Z).data)
    assert_equal(K_owarp.data, Warping(k, owarping_coef=owarping_coef)(X, Z).data)
    assert_equal(K_vscale.data, VerticalScaling(k, vscaling_fn=vscaling_fn)(X, Z).data)
    assert_equal(K.exp().data, Exponent(k)(X, Z).data)

    # test get_subkernel
    k1 = Sum(Warping(k, iwarping_fn=iwarping_fn), TEST_CASES[7][0])
    assert k1.get_subkernel(k.name) is k
