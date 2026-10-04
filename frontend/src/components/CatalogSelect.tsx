import { useState } from "react";
import { toast } from "sonner";
import { Plus, X } from "lucide-react";
import { useOptions, useCatalogMutations, catalogError } from "@/lib/useCatalogs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type Props = {
  tip: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  testid: string;
  className?: string;
};

/**
 * Tanım listesinden seçim + "Yeni ekle" — sipariş/kalem ekranından ayrılmadan
 * listede olmayan bir değer (ürün, renk, kumaş, tedarikçi…) oluşturur ve seçer.
 */
export function CatalogSelect({ tip, label, value, onChange, testid, className }: Props) {
  const options = useOptions(tip);
  const [adding, setAdding] = useState(false);
  const [yeni, setYeni] = useState("");
  const { create } = useCatalogMutations(tip);

  const ekle = () => {
    const ad = yeni.trim();
    if (!ad) return;
    create.mutate(ad, {
      onSuccess: (item) => {
        onChange(item.label);
        setYeni("");
        setAdding(false);
        toast.success(`${label} listesine eklendi: ${item.label}`);
      },
      onError: (err) => toast.error(catalogError(err, "Tanım eklenemedi")),
    });
  };

  return (
    <div className={className ? `space-y-1.5 ${className}` : "space-y-1.5"}>
      <div className="flex items-center justify-between gap-2">
        <Label>{label}</Label>
        <button
          type="button"
          className="flex items-center gap-1 text-[11px] text-muted-foreground transition-colors duration-150 hover:text-primary"
          onClick={() => setAdding(!adding)}
          data-testid={`${testid}-toggle-add`}
        >
          {adding ? <X className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
          {adding ? "Vazgeç" : "Yeni ekle"}
        </button>
      </div>

      {adding ? (
        <div className="flex gap-2">
          <Input
            autoFocus
            value={yeni}
            placeholder={`Yeni ${label.toLowerCase()} adı…`}
            onChange={(e) => setYeni(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                ekle();
              }
            }}
            data-testid={`${testid}-new-input`}
          />
          <Button
            type="button"
            size="sm"
            disabled={create.isPending || !yeni.trim()}
            onClick={ekle}
            data-testid={`${testid}-new-save`}
          >
            {create.isPending ? "…" : "Ekle"}
          </Button>
        </div>
      ) : (
        <Select value={value} onValueChange={(v: string) => onChange(v)}>
          <SelectTrigger data-testid={testid}>
            <SelectValue placeholder="Seçiniz…" />
          </SelectTrigger>
          <SelectContent className="max-h-72">
            {options.map((o) => (
              <SelectItem key={o.id} value={o.label}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  );
}

export default CatalogSelect;
