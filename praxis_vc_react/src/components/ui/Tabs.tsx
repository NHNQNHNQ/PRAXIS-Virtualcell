import type { ReactNode } from "react";


export type TabItem = {
  id: string;
  label: ReactNode;
};

export type TabsProps = {
  tabs: TabItem[];
  active: string;
  onChange: (id: string) => void;
};

export default function Tabs({ tabs, active, onChange }: TabsProps) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={t.id === active}
          className={t.id === active ? "tab active" : "tab"}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
