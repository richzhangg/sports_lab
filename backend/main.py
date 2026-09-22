"""FastAPI service for the Sports Opportunity Modeling Lab."""
from __future__ import annotations

import os

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except Exception:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import data
import experiments
import geo_api
import modeling

app = FastAPI(title="Sports Opportunity Modeling Lab API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    outcome: str
    predictors: list[str] = []
    family: str
    train_years: list[int] = Field(min_length=1)
    test_year: int
    standardize: bool = True
    include_baseline: bool = True
    cv_folds: int = 0
    equation: str | None = None
    variables: dict[str, str] = {}


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/metadata")
def metadata():
    return {
        "source": data.source_info(),
        "predictors": [v.__dict__ for v in data.predictors()],
        "outcomes": [v.__dict__ for v in data.outcomes()],
        "families": [
            {"key": "linear", "label": "Linear (OLS)",
             "note": "Ordinary least squares on the outcome. Works for any outcome; "
                     "a natural simple baseline."},
            {"key": "poisson", "label": "Poisson",
             "note": "Log-linear count model with log(youth_population) offset -> models a "
                     "representation rate. Assumes mean = variance."},
            {"key": "negbin", "label": "Negative Binomial",
             "note": "Count model that adds an overdispersion parameter; preferred "
                     "when the dispersion ratio is well above 1."},
            {"key": "zip", "label": "Zero-inflated Poisson",
             "note": "Logit 'structural zero' component + Poisson counts. For when "
                     "far more communities produce zero D1 players than a plain "
                     "count model expects."},
            {"key": "zinb", "label": "Zero-inflated Neg. Binomial",
             "note": "Zero-inflation plus overdispersion — the most flexible count "
                     "model here."},
            {"key": "custom", "label": "Custom equation",
             "note": "You assign symbols to variables (x = median income, y = poverty "
                     "rate, …) and type any formula. The app evaluates it for every "
                     "community and compares to the actual NCAA counts — nothing is "
                     "fitted."},
        ],
        "equation_functions": sorted(__import__("equation").ALLOWED_FUNCS),
        "years": data.available_years(),
        "count_outcome": modeling.COUNT_OUTCOME,
    }


@app.get("/api/preview")
def preview(limit: int = 25):
    df = data.get_dataframe()
    return {
        "columns": list(df.columns),
        "rows": df.head(limit).to_dict(orient="records"),
        "source": data.source_info(),
    }


@app.get("/api/rosters")
def rosters(sample: int = 40):
    return data.rosters_info(sample=sample)


@app.get("/api/players")
def players(q: str = "", limit: int = 60):
    return data.players_search(q, limit=limit)


@app.get("/api/county/{fips}")
def county(fips: str):
    return data.county_detail(fips)


@app.get("/api/geo")
def geo(year: int | None = None):
    return geo_api.build(year=year)


@app.post("/api/run")
def run(req: RunRequest):
    try:
        return modeling.run_experiment(
            outcome=req.outcome,
            predictors=req.predictors,
            family=req.family,
            train_years=req.train_years,
            test_year=req.test_year,
            standardize=req.standardize,
            include_baseline=req.include_baseline,
            cv_folds=req.cv_folds,
            equation=req.equation,
            variables=req.variables,
        )
    except modeling.ModelError as e:
        raise HTTPException(status_code=400, detail=str(e))


class SaveExperimentRequest(BaseModel):
    label: str
    result: dict


@app.get("/api/experiments")
def list_experiments():
    return experiments.list_all()


@app.post("/api/experiments")
def create_experiment(req: SaveExperimentRequest):
    return experiments.save(req.label, req.result, data.ACTIVE_SOURCE.key)


@app.get("/api/experiments/{rid}")
def get_experiment(rid: str):
    rec = experiments.get(rid)
    if not rec:
        raise HTTPException(status_code=404, detail="experiment not found")
    return rec


@app.delete("/api/experiments/{rid}")
def delete_experiment(rid: str):
    if not experiments.delete(rid):
        raise HTTPException(status_code=404, detail="experiment not found")
    return {"deleted": rid}


@app.delete("/api/experiments")
def clear_experiments():
    return {"deleted": experiments.clear()}
