import { Hero, BigStatement, MethodSection, DataSection, CTA } from "@/components/landing";

export default function LandingPage() {
  return (
    <main className="pb-10">
      <Hero />

      <BigStatement>
        Some communities send a dozen players to Division I tennis. Most send none. The pattern is
        not random — it tracks income, education, and whether there was a court to play on.
      </BigStatement>

      <MethodSection />
      <DataSection />
      <CTA />

      <footer className="mx-auto max-w-[1440px] border-t border-line px-5 py-6 text-[12px] leading-relaxed text-muted sm:px-8">
        Estimation via Python <code>statsmodels</code>; free-form equations via <code>numexpr</code>.
        Data: NCAA Division I roster pages, U.S. Census ACS 5-year, OpenStreetMap (ODbL). Training
        and validation years are kept strictly separate.
      </footer>
    </main>
  );
}
