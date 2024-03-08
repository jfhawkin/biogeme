"""

Mixtures of logit with Monte-Carlo 500 Halton draws
===================================================

Estimation of a mixtures of logit models where the integral is
approximated using MonteCarlo integration with Halton draws.

:author: Michel Bierlaire, EPFL
:date: Mon Dec 11 08:13:26 2023
"""

import biogeme.biogeme_logging as blog
from biogeme.expressions import bioDraws
from b07estimation_specification import get_biogeme

# %%
logger = blog.get_screen_logger(level=blog.INFO)
logger.info('Example b07estimation_monte_carlo_halton_500.py')

# %%
R = 500

# %%
the_draws = bioDraws('b_time_rnd', 'NORMAL_HALTON2')
the_biogeme = get_biogeme(the_draws=the_draws, number_of_draws=R)
the_biogeme.modelName = 'b07estimation_monte_carlo_halton_500'

# %%
results = the_biogeme.estimate()

# %%
print(results.short_summary())

# %%
pandas_results = results.get_estimated_parameters()
pandas_results
