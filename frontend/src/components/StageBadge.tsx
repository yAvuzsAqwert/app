import { stageOf } from "@/lib/constants";
import { useCatalog } from "@/lib/useCatalogs";
import { cn } from "@/lib/utils";

export function StageBadge({ durum, className }: { durum: string; className?: string }) {
  const stage = stageOf(durum);
  const dinamik = useCatalog("asama").find((s) => s.deger === durum);
  return (
    <span
      data-testid={`stage-badge-${durum}`}
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded-full border px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wide",
        stage.tone,
        className,
      )}
    >
      {dinamik?.label ?? stage.label}
    </span>
  );
}
