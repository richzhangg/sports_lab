"use client";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import CompareView from "@/components/CompareView";
import {
  listExperiments, getExperiment, deleteExperiment, clearExperiments,
  type SavedExperiment,
} from "@/lib/api";

export default function ComparePage() {
  const router = useRouter();
  const [saved, setSaved] = useState<SavedExperiment[]>([]);

  const refresh = useCallback(() => {
    listExperiments().then(setSaved).catch(() => {});
  }, []);
  useEffect(refresh, [refresh]);

  const onOpen = useCallback(
    async (id: string) => {
      const rec = await getExperiment(id);
      try {
        const prev = JSON.parse(sessionStorage.getItem("sol.lab.v1") || "{}");
        sessionStorage.setItem("sol.lab.v1", JSON.stringify({ ...prev, result: rec.result }));
      } catch {}
      router.push("/lab");
    },
    [router],
  );

  const onRemove = useCallback(async (id: string) => {
    await deleteExperiment(id);
    listExperiments().then(setSaved).catch(() => {});
  }, []);
  const onClear = useCallback(async () => {
    await clearExperiments();
    listExperiments().then(setSaved).catch(() => {});
  }, []);

  return (
    <main className="mx-auto max-w-[1440px] px-5 py-8 sm:px-8">
      <div className="mb-6">
        <p className="eyebrow mb-1.5">Compare</p>
        <h1 className="text-[26px] leading-tight text-ink sm:text-[30px]">
          Which model actually generalizes?
        </h1>
      </div>
      <CompareView runs={saved} onRemove={onRemove} onClear={onClear} onOpen={onOpen} />
    </main>
  );
}
