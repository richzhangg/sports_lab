"""
Generate the DEMO DATASET for the Sports Opportunity Modeling Lab.

THIS IS SYNTHETIC DATA. It is NOT real NCAA roster data and NOT real U.S. Census
data. It is generated from a known statistical process so that the modeling
workflow (estimation, validation, overfitting, model comparison) can be
exercised end to end. Replace this module + demo_dataset.csv with a real data
loader without touching the modeling code (see data.py).

Data-generating process (per community, per year)
------------------------------------------------
  log(mu) = log(population/100000)                      # offset -> counts scale to a rate
            + b0
            + b_income   * z(median_income)
            + b_poverty  * z(poverty_rate)
            + b_bachelors* z(pct_bachelors)
            + b_courts   * z(tennis_courts_per_100k)    # "tennis access"
            + b_density  * z(pop_density)
            + small year drift
  d1_players ~ NegativeBinomial(mean=mu, dispersion=alpha)

Nuisance predictors (noise_1..noise_6) are pure noise. A model that keeps adding
them will improve training fit slightly while degrading validation performance —
this is the overfitting demonstration described in the design document.
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260826)
YEARS = [2022, 2023, 2024, 2025]
N_COMMUNITIES = 320

STATES = ["CA", "TX", "FL", "NY", "IL", "GA", "NC", "OH", "PA", "MI",
          "WA", "AZ", "CO", "MA", "VA", "TN", "MN", "WI", "MO", "OR"]


def _z(x: np.ndarray) -> np.ndarray:
    return (x - x.mean()) / x.std()


def build() -> pd.DataFrame:
    # ---- static community attributes -------------------------------------
    pop = RNG.lognormal(mean=11.0, sigma=0.8, size=N_COMMUNITIES).clip(4_000, 4_000_000)
    median_income = RNG.normal(68_000, 22_000, N_COMMUNITIES).clip(22_000, 250_000)
    # poverty correlated negatively with income
    poverty_rate = (28 - 0.00022 * (median_income - 68_000)
                    + RNG.normal(0, 4, N_COMMUNITIES)).clip(1.5, 45)
    pct_bachelors = (32 + 0.00035 * (median_income - 68_000)
                     + RNG.normal(0, 7, N_COMMUNITIES)).clip(6, 82)
    pop_density = RNG.lognormal(mean=6.5, sigma=1.1, size=N_COMMUNITIES).clip(20, 45_000)
    tennis_courts = (2.5 + 0.00004 * (median_income - 68_000)
                     + RNG.normal(0, 1.6, N_COMMUNITIES)).clip(0.05, 14)

    state = RNG.choice(STATES, size=N_COMMUNITIES)
    community_id = np.array([f"C{ i:04d}" for i in range(N_COMMUNITIES)])
    community_name = np.array([f"{s} Community {i:03d}" for i, s in enumerate(state)])

    zi, zp, zb, zc, zd = (_z(median_income), _z(poverty_rate), _z(pct_bachelors),
                          _z(tennis_courts), _z(pop_density))

    # ---- true coefficients ---------------------------------------------
    B0 = -0.55
    B_INCOME, B_POVERTY, B_BACH, B_COURTS, B_DENSITY = 0.42, -0.30, 0.18, 0.35, -0.08
    ALPHA = 0.35  # NB overdispersion

    rows = []
    for yi, year in enumerate(YEARS):
        year_drift = 0.02 * (yi - 1.5)
        log_mu = (np.log(pop / 100_000) + B0 + year_drift
                  + B_INCOME * zi + B_POVERTY * zp + B_BACH * zb
                  + B_COURTS * zc + B_DENSITY * zd
                  + RNG.normal(0, 0.05, N_COMMUNITIES))
        mu = np.exp(log_mu).clip(1e-4, None)
        # NB via gamma-poisson mixture
        shape = 1.0 / ALPHA
        gamma_noise = RNG.gamma(shape, scale=1.0 / shape, size=N_COMMUNITIES)
        d1 = RNG.poisson(mu * gamma_noise)

        df = pd.DataFrame({
            "community_id": community_id,
            "community_name": community_name,
            "state": state,
            "year": year,
            "population": pop.round(0).astype(int),
            "median_income": median_income.round(0).astype(int),
            "poverty_rate": poverty_rate.round(2),
            "pct_bachelors": pct_bachelors.round(2),
            "tennis_courts_per_100k": tennis_courts.round(3),
            "pop_density": pop_density.round(1),
            "d1_players": d1.astype(int),
        })
        for k in range(1, 7):
            df[f"noise_{k}"] = RNG.normal(0, 1, N_COMMUNITIES).round(4)
        df["d1_rate_per_100k"] = (df["d1_players"] / df["population"] * 100_000).round(4)
        rows.append(df)

    out = pd.concat(rows, ignore_index=True)
    return out


if __name__ == "__main__":
    import os
    path = os.path.join(os.path.dirname(__file__), "data", "demo_dataset.csv")
    build().to_csv(path, index=False)
    print(f"wrote {path}")
