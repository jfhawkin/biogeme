"""

biogeme.tools
=============

Examples of use of several functions.

This is designed for programmers who need examples of use of the
functions of the module. The examples are designed to illustrate the
syntax. They do not correspond to any meaningful model.

:author: Michel Bierlaire
:date: Sat Dec  2 13:09:42 2023
"""

import numpy as np
import pandas as pd

import biogeme.biogeme_logging as blog
import biogeme.exceptions as excep
import biogeme.tools.derivatives
import biogeme.tools.primes
from biogeme.function_output import FunctionOutput
from biogeme.version import get_text

# %%
# Version of Biogeme.
print(get_text())

# %%
logger = blog.get_screen_logger(level=blog.INFO)


# %%
# Define a function and its derivatives:
#
# .. math:: f = \log(x_0) + \exp(x_1),
#
# .. math:: g = \left( \begin{array}{c}\frac{1}{x_0} \\
#     \exp(x_1)\end{array}\right),
#
# .. math:: h=\left(\begin{array}{cc} -\frac{1}{x_0^2} & 0 \\ 0 &
#     \exp(x_1)\end{array}\right).
def my_function(x: np.ndarray) -> FunctionOutput:
    """Implementation of the test function.

    :param x: point at which the function and its derivatives must be evaluated.
    """
    f = np.log(x[0]) + np.exp(x[1])
    g = np.empty(2)
    g[0] = 1.0 / x[0]
    g[1] = np.exp(x[1])
    h = np.empty((2, 2))
    h[0, 0] = -1.0 / x[0] ** 2
    h[0, 1] = 0.0
    h[1, 0] = 0.0
    h[1, 1] = np.exp(x[1])
    return FunctionOutput(function=f, gradient=g, hessian=h)


# %%
# Evaluate the function at the point
#
# .. math:: x = \left( \begin{array}{c}1.1 \\ 1.1 \end{array}\right).
#
x = np.array([1.1, 1.1])
the_output = my_function(x)

# %%
the_output.function

# %%
# We use the `DataFrame` for a nicer display.
pd.DataFrame(the_output.gradient)

# %%
pd.DataFrame(the_output.hessian)

# %%
# Calculates an approximation of the gradient by finite differences.
g_fd = biogeme.tools.derivatives.findiff_g(my_function, x)

# %%
pd.DataFrame(g_fd)

# %%
# Check the precision of the approximation
pd.DataFrame(the_output.gradient - g_fd)

# %%
# Calculates an approximation of the Hessian by finite differences.
h_fd = biogeme.tools.derivatives.findiff_h(my_function, x)

# %%
pd.DataFrame(h_fd)

# %%
# Check the precision of the approximation
pd.DataFrame(the_output.hessian - h_fd)

# %%
# There is a function that checks the analytical derivatives by
# comparing them to their finite difference approximation.
f, g, h, gdiff, hdiff = biogeme.tools.derivatives.check_derivatives(
    my_function, x, names=None, logg=True
)

# %%
# To help reading the reporting, it is possible to give names to variables.

# %%
f, g, h, gdiff, hdiff = biogeme.tools.derivatives.check_derivatives(
    my_function, x, names=['First', 'Second'], logg=True
)

# %%
pd.DataFrame(gdiff)

# %%
hdiff

# %%
# Prime numbers: calculate prime numbers lesser or equal to an upper bound.
myprimes = biogeme.tools.primes.calculate_prime_numbers(10)
myprimes

# %%
myprimes = biogeme.tools.primes.calculate_prime_numbers(100)
myprimes

# %%
# Calculate a given number of prime numbers.
myprimes = biogeme.tools.primes.get_prime_numbers(7)
myprimes

# %%
# Counting groups of data.
alist = [1, 2, 2, 3, 3, 3, 4, 1, 1]

# %%
df = pd.DataFrame(
    {
        'ID': [1, 1, 2, 3, 3, 1, 2, 3],
        'value': [1000, 2000, 3000, 4000, 5000, 5000, 10000, 20000],
    }
)

# %%
biogeme.tools.count_number_of_groups(df, 'ID')

# %%
biogeme.tools.count_number_of_groups(df, 'value')

# %%
# Likelihood ratio test.
model1 = (-1340.8, 5)
model2 = (-1338.49, 7)

# %%
# A likelihood ratio test is performed. The function returns the
# outcome of the test, the statistic, and the threshold.
biogeme.tools.likelihood_ratio.likelihood_ratio_test(model1, model2)

# %%
# The default level of significance is 0.95. It can be changed.
biogeme.tools.likelihood_ratio.likelihood_ratio_test(
    model1, model2, significance_level=0.9
)

# %%
# The order in which the models are presented is irrelevant.
biogeme.tools.likelihood_ratio.likelihood_ratio_test(model2, model1)

# %%
# But the unrestricted model must have a higher loglikelihood than the
# restricted one.
model1 = (-1340.8, 7)
model2 = (-1338.49, 5)

# %%
try:
    biogeme.tools.likelihood_ratio.likelihood_ratio_test(model1, model2)
except excep.BiogemeError as e:
    print(e)
