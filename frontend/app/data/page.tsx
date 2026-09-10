import DataPreview from "@/components/DataPreview";
import PlayerSearch from "@/components/PlayerSearch";

export default function DataPage() {
  return (
    <main className="mx-auto max-w-[1440px] px-5 py-8 sm:px-8">
      <div className="mb-6">
        <p className="eyebrow mb-1.5">Data</p>
        <h1 className="text-[26px] leading-tight text-ink sm:text-[30px]">
          The NCAA record, joined to the Census.
        </h1>
      </div>
      <div className="space-y-4">
        <PlayerSearch />
        <DataPreview />
      </div>
    </main>
  );
}
