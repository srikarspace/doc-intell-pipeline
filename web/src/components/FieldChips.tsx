import { Check } from "lucide-react";
import type { FieldInfo } from "../api.ts";

type Props = {
  fields: FieldInfo[];
  chosen: Set<string>;
  onChange: (chosen: Set<string>) => void;
};

/** The 12 fields as chips, in their 4 groups. All are on at the start. */
export function FieldChips({ fields, chosen, onChange }: Props) {
  const groups = [...new Set(fields.map((f) => f.group))];
  const toggle = (name: string) => {
    const copy = new Set(chosen);
    if (copy.has(name)) copy.delete(name);
    else copy.add(name);
    onChange(copy);
  };

  return (
    <section>
      <div className="mb-2.5 flex items-center gap-3 text-xs font-semibold tracking-wider text-base-content/50 uppercase">
        1 · Fields to find
        <span className="ml-auto flex gap-3 text-[13px] font-medium tracking-normal normal-case">
          <button className="link link-primary no-underline" onClick={() => onChange(new Set(fields.map((f) => f.name)))}>
            Select all
          </button>
          <button className="link link-primary no-underline" onClick={() => onChange(new Set())}>
            Clear
          </button>
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {groups.map((group) => (
          <div key={group} className="grid content-start gap-1.5 rounded-xl border border-base-300 bg-base-100 p-2.5">
            <h3 className="mb-0.5 ml-1 text-xs font-medium text-base-content/50">{group}</h3>
            {fields
              .filter((f) => f.group === group)
              .map((f) => {
                const on = chosen.has(f.name);
                return (
                  <button
                    key={f.name}
                    aria-pressed={on}
                    onClick={() => toggle(f.name)}
                    className={`flex items-center gap-2 rounded-lg border px-2 py-1.5 text-left text-[13px] ${
                      on ? "border-primary bg-primary/10 text-base-content" : "border-base-300 text-base-content/70"
                    }`}
                  >
                    <span
                      className={`grid size-4 flex-none place-items-center rounded-[5px] border-[1.5px] ${
                        on ? "border-primary bg-primary text-primary-content" : "border-base-content/40"
                      }`}
                    >
                      {on && <Check size={11} strokeWidth={3.5} />}
                    </span>
                    {f.label}
                  </button>
                );
              })}
          </div>
        ))}
      </div>
      {chosen.size === 0 && <p className="mt-2 text-[13px] text-warning">Pick at least one field.</p>}
    </section>
  );
}
