import { useState, type ReactNode } from "react";
import { glossary, type GlossaryKey } from "./glossary";

/** A word with a dotted underline. Hover, focus or tap shows a short plain-language definition. */
export function Term({ id, children }: { id: GlossaryKey; children?: ReactNode }) {
  const [open, setOpen] = useState(false);
  const g = glossary[id];
  return (
    <span className="term" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        className="term-word"
        aria-label={`${typeof children === "string" ? children : g.term}: what does this mean?`}
        onClick={(e) => (e.stopPropagation(), setOpen((o) => !o))}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      >
        {children ?? g.term}
      </button>
      {open && (
        <span className="term-pop" role="tooltip">
          {g.text}
        </span>
      )}
    </span>
  );
}

/** Every term in one list: opened from the "Glossary" button in 2b. */
export function GlossaryPanel({ onClose }: { onClose: () => void }) {
  return (
    <aside className="glossary">
      <div className="glossary-head">
        <b>Glossary</b>
        <button className="link" onClick={onClose}>Close</button>
      </div>
      {Object.values(glossary).map((g) => (
        <div key={g.term} className="glossary-row">
          <b>{g.term}</b>
          <span>{g.text}</span>
        </div>
      ))}
    </aside>
  );
}
