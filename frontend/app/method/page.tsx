import Link from "next/link";
import { Reveal } from "@/components/landing";

export const metadata = { title: "Method — Sports Opportunity Modeling Lab" };

export default function MethodPage() {
  return (
    <main className="mx-auto max-w-[760px] px-5 py-12 sm:px-8">
      <p className="eyebrow mb-2">Method</p>
      <h1 className="text-[30px] leading-tight text-ink sm:text-[36px]">
        How the lab tests a model
      </h1>
      <p className="mt-4 text-[15px] leading-relaxed text-ink-2">
        The unit of analysis is a U.S. county in a given year. Each row of the dataset joins three
        public sources onto that county-year: the NCAA Division I tennis roster count (players whose
        listed hometown geocodes to the county), the U.S. Census ACS 5-year socioeconomic
        predictors, and an OpenStreetMap count of tennis facilities.
      </p>

      <div className="mt-10 space-y-8">
        {SECTIONS.map((s, i) => (
          <Reveal key={s.h} delay={i * 0.05}>
            <div className="flex gap-4">
              <span className="step-no mt-1">{String(i + 1).padStart(2, "0")}</span>
              <div>
                <h2 className="font-display text-[19px] text-ink">{s.h}</h2>
                <p className="mt-1.5 text-[13.5px] leading-relaxed text-ink-2">{s.p}</p>
              </div>
            </div>
          </Reveal>
        ))}
      </div>

      <div className="mt-12 rounded-lg border border-line bg-raised p-5 text-[13px] leading-relaxed text-ink-2">
        <p className="eyebrow mb-2">On research integrity</p>
        Training years and the validation year never mix — parameters are estimated on training rows
        only, and every out-of-sample number uses the held-out year alone. Model quality is reported
        with statistically appropriate measures (RMSE, MAE, Poisson deviance, coefficient
        uncertainty), never a single &ldquo;accuracy&rdquo; percentage. The demo dataset is clearly
        labelled and never presented as real NCAA or Census data.
      </div>

      <Link href="/lab" className="btn btn-primary mt-10 !px-5 !py-2.5 text-[13px]">
        Open the Lab &nbsp;→
      </Link>
    </main>
  );
}

const SECTIONS = [
  {
    h: "Propose a model",
    p: "Choose an outcome and a set of predictors and a model family (linear, Poisson, negative binomial, zero-inflated) — or switch to the custom-equation mode and type the whole formula yourself. The app does not judge the equation; it just evaluates it.",
  },
  {
    h: "Estimate parameters",
    p: "For the statistical families, coefficients are fit on the training years with Python statsmodels — Poisson and negative-binomial models carry a log(youth population) offset (residents 0-17, not the whole county) so coefficients describe a representation rate among the population actually old enough to be a recruit. Custom equations fit nothing; the constants are yours.",
  },
  {
    h: "Validate out of sample",
    p: "The fitted model predicts a year it has never seen. Predicted counts are laid beside the real NCAA counts county by county: a predicted-vs-observed scatter, residuals versus fitted values, and error metrics on the held-out year.",
  },
  {
    h: "Cross-validate",
    p: "Optionally, k-fold cross-validation over the training rows and leave-one-year-out validation across every year — the latter refits the model with each year held out in turn, the most honest generalization estimate and the clearest view of instability.",
  },
  {
    h: "Compare and select",
    p: "Save several models and read them side by side. When training error keeps falling while validation and cross-validated error rise, the model is memorizing the training years — the overfitting story from the original design.",
  },
];
