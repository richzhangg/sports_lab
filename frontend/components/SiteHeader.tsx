"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";

const NAV = [
  { href: "/lab", label: "Lab" },
  { href: "/map", label: "Map" },
  { href: "/data", label: "Data" },
  { href: "/compare", label: "Compare" },
  { href: "/method", label: "Method" },
];

export default function SiteHeader() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-40 transition-colors duration-300 ${
        scrolled ? "border-b border-line bg-paper/85 backdrop-blur-md" : "border-b border-transparent"
      }`}
    >
      <div className="mx-auto flex max-w-[1440px] items-center justify-between px-5 py-3 sm:px-8">
        <Link href="/" className="group flex items-baseline gap-2">
          <span className="font-display text-[17px] font-medium tracking-tight text-ink">
            Sports Opportunity Lab
          </span>
          <span className="hidden font-mono text-[10px] uppercase tracking-eyebrow text-muted sm:inline">
            modeling
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV.map((n) => {
            const active = pathname === n.href || pathname.startsWith(n.href + "/");
            return (
              <Link
                key={n.href}
                href={n.href}
                className={`relative rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors ${
                  active ? "text-ink" : "text-muted hover:text-ink-2"
                }`}
              >
                {n.label}
                {active && (
                  <motion.span
                    layoutId="nav-underline"
                    className="absolute inset-x-2 -bottom-0.5 h-[2px] rounded-full bg-court"
                    transition={{ type: "spring", stiffness: 400, damping: 32 }}
                  />
                )}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
