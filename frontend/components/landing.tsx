"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { motion, useInView, useScroll, useTransform, animate } from "framer-motion";
import CountyDotMap from "@/components/CountyDotMap";

const EASE = [0.22, 0.61, 0.24, 1] as const;

export function Hero() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const mapY = useTransform(scrollYProgress, [0, 1], [0, 90]);
  const mapOpacity = useTransform(scrollYProgress, [0, 0.8], [1, 0.15]);
  const textY = useTransform(scrollYProgress, [0, 1], [0, -40]);

  return (
    <section ref={ref} className="relative mx-auto max-w-[1440px] px-5 pb-10 pt-10 sm:px-8 sm:pt-16">
      <div className="grid items-center gap-8 lg:grid-cols-[1.05fr_1.35fr]">
        <motion.div style={{ y: textY }} className="relative z-10">
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: EASE }}
            className="eyebrow mb-3"
          >
            A computational research platform
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.05 }}
            className="text-[34px] leading-[1.08] text-ink sm:text-[46px]"
          >
            Where do Division&nbsp;I<span className="text-court"> tennis</span> players come from?
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.12 }}
            className="mt-4 max-w-md text-[15px] leading-relaxed text-ink-2"
          >
            Construct a mathematical model of community-level representation in college athletics —
            then test it, year by year, against the real NCAA record.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.2 }}
            className="mt-7 flex flex-wrap items-center gap-3"
          >
            <Link href="/lab" className="btn btn-primary !px-5 !py-2.5 text-[13px]">
              Open the Lab &nbsp;→
            </Link>
            <Link href="/data" className="btn btn-ghost !px-4 !py-2.5 text-[13px]">
              See the data
            </Link>
          </motion.div>
        </motion.div>

        <motion.div style={{ y: mapY, opacity: mapOpacity }} className="relative">
          <CountyDotMap className="mx-auto max-w-[720px]" />
          <p className="mt-2 text-center font-mono text-[10.5px] text-muted">
            Each glowing point is a U.S. county; size = NCAA D1 tennis players from that community
            (2026 rosters).
          </p>
        </motion.div>
      </div>
    </section>
  );
}

export function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.12 });
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 900); // safety: reveal even if never scrolled into view
    return () => clearTimeout(t);
  }, []);
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 22 }}
      animate={inView || mounted ? { opacity: 1, y: 0 } : { opacity: 0, y: 22 }}
      transition={{ duration: 0.6, ease: EASE, delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function Counter({ to, suffix = "" }: { to: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.5 });
  const [val, setVal] = useState(0);
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setArmed(true), 900);
    return () => clearTimeout(t);
  }, []);
  useEffect(() => {
    if (!inView && !armed) return;
    const controls = animate(0, to, {
      duration: 1.4,
      ease: EASE,
      onUpdate: (v) => setVal(v),
    });
    return () => controls.stop();
  }, [inView, armed, to]);
  return (
    <span ref={ref} className="tabular-nums">
      {Math.round(val).toLocaleString()}
      {suffix}
    </span>
  );
}

export function BigStatement({ children }: { children: React.ReactNode }) {
  return (
    <section className="mx-auto max-w-[1440px] px-5 py-20 sm:px-8">
      <Reveal>
        <p className="max-w-3xl font-display text-[26px] leading-snug text-ink sm:text-[34px]">
          {children}
        </p>
      </Reveal>
    </section>
  );
}

export function MethodSection() {
  const steps = [
    ["Propose", "Pick predictors and a model family — or type your own equation. This is your claim about how representation works."],
    ["Estimate", "The app fits the model on a window of training years using Python statsmodels. Nothing about your equation is second-guessed."],
    ["Validate", "It predicts a held-out year the model has never seen, and lays the predictions next to the real NCAA counts."],
    ["Compare", "Stack rival models. Watch training error fall while validation error rises — the signature of overfitting."],
  ];
  return (
    <section className="mx-auto max-w-[1440px] px-5 py-16 sm:px-8">
      <Reveal className="mb-8">
        <p className="eyebrow mb-2">The research loop</p>
        <h2 className="max-w-xl text-[24px] leading-snug text-ink sm:text-[30px]">
          Real model development, not a dataset summary.
        </h2>
      </Reveal>
      <div className="grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
        {steps.map(([t, d], i) => (
          <Reveal key={t} delay={i * 0.08} className="bg-surface p-5">
            <span className="step-no">{String(i + 1).padStart(2, "0")}</span>
            <div className="mt-3 font-display text-[18px] text-ink">{t}</div>
            <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted">{d}</p>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

export function DataSection() {
  return (
    <section className="border-y border-line bg-raised">
      <div className="mx-auto max-w-[1440px] px-5 py-16 sm:px-8">
        <Reveal className="mb-8">
          <p className="eyebrow mb-2">Built from public sources · no API keys</p>
          <h2 className="max-w-xl text-[24px] leading-snug text-ink sm:text-[30px]">
            One county-year panel, three real datasets joined.
          </h2>
        </Reveal>
        <div className="grid gap-8 sm:grid-cols-3">
          {[
            { n: 9137, s: "", label: "NCAA D1 tennis players", sub: "placed into a U.S. county, 2022–2026, from 278 program rosters" },
            { n: 3222, s: "", label: "U.S. counties", sub: "with Census ACS income, poverty, education & density" },
            { n: 199921, s: "", label: "tennis facilities", sub: "from OpenStreetMap — the “access” predictor" },
          ].map((x, i) => (
            <Reveal key={x.label} delay={i * 0.1}>
              <div className="font-display text-[40px] leading-none text-ink">
                <Counter to={x.n} suffix={x.s} />
              </div>
              <div className="mt-2 text-[13px] font-medium text-ink">{x.label}</div>
              <div className="mt-0.5 text-[12px] leading-relaxed text-muted">{x.sub}</div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

export function CTA() {
  return (
    <section className="mx-auto max-w-[1440px] px-5 py-24 text-center sm:px-8">
      <Reveal>
        <h2 className="mx-auto max-w-lg text-[26px] leading-snug text-ink sm:text-[32px]">
          Start with a hypothesis. See where the data disagrees.
        </h2>
        <Link href="/lab" className="btn btn-primary mt-6 !px-6 !py-3 text-[14px]">
          Open the Lab &nbsp;→
        </Link>
      </Reveal>
    </section>
  );
}
