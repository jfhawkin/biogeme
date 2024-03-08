"""

Antithetic draws explicitly generated
=====================================

Calculation of a simple integral using Monte-Carlo integration. It
illustrates how to use antothetic draws, explicitly generared.

:author: Michel Bierlaire, EPFL
:date: Thu Apr 13 20:49:50 2023
"""

import numpy as np
import pandas as pd
import biogeme.database as db
import biogeme.biogeme as bio
from biogeme import draws
from biogeme.expressions import exp, bioDraws, MonteCarlo
from biogeme.native_draws import RandomNumberGeneratorTuple

# %%
R = 10000

# %%
# We create a fake database with one entry, as it is required to store
# the draws
df = pd.DataFrame()
df['FakeColumn'] = [1.0]
database = db.Database('fake_database', df)


# %%
def halton13(sample_size: int, number_of_draws: int) -> np.array:
    """
    The user can define new draws. For example, Halton draws
    with base 13, skipping the first 10 draws.

    :param sample_size: number of observations for which draws must be
                       generated.
    :param number_of_draws: number of draws to generate.

    """
    return draws.get_halton_draws(sample_size, number_of_draws, base=13, skip=10)


# %%
my_draws = {
    'HALTON13': RandomNumberGeneratorTuple(
        halton13, 'Halton draws, base 13, skipping 10'
    )
}
database.set_random_number_generators(my_draws)

# %%
U = bioDraws('U', 'UNIFORM')
integrand = exp(U) + exp(1 - U)
simulated_integral = MonteCarlo(integrand) / 2.0

# %%
U_halton13 = bioDraws('U_halton13', 'HALTON13')
integrand_halton13 = exp(U_halton13) + exp(1 - U_halton13)
simulated_integral_halton13 = MonteCarlo(integrand_halton13) / 2.0

# %%
U_mlhs = bioDraws('U_mlhs', 'UNIFORM_MLHS')
integrand_mlhs = exp(U_mlhs) + exp(1 - U_mlhs)
simulated_integral_mlhs = MonteCarlo(integrand_mlhs) / 2.0

# %%
true_integral = exp(1.0) - 1.0

# %%
error = simulated_integral - true_integral

# %%
error_halton13 = simulated_integral_halton13 - true_integral

# %%
error_mlhs = simulated_integral_mlhs - true_integral

# %%
simulate = {
    'Analytical Integral': true_integral,
    'Simulated Integral': simulated_integral,
    'Error             ': error,
    'Simulated Integral (Halton13)': simulated_integral_halton13,
    'Error (Halton13)             ': error_halton13,
    'Simulated Integral (MLHS)': simulated_integral_mlhs,
    'Error (MLHS)             ': error_mlhs,
}

# %%
biosim = bio.BIOGEME(database, simulate)
biosim.modelName = 'b03antithetic_explicit'

# %%
results = biosim.simulate(the_beta_values={})
results

# %%
print(f"Analytical integral: {results.iloc[0]['Analytical Integral']:.6f}")
print(
    f"         \t{'Uniform (Anti)':>15}\t{'Halton13 (Anti)':>15}\t{'MLHS (Anti)':>15}"
)
print(
    f"Simulated\t{results.iloc[0]['Simulated Integral']:>15.6g}\t"
    f"{results.iloc[0]['Simulated Integral (Halton13)']:>15.6g}\t"
    f"{results.iloc[0]['Simulated Integral (MLHS)']:>15.6g}"
)
print(
    f"Error\t\t{results.iloc[0]['Error             ']:>15.6g}\t"
    f"{results.iloc[0]['Error (Halton13)             ']:>15.6g}\t"
    f"{results.iloc[0]['Error (MLHS)             ']:>15.6g}"
)
