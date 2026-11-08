import type { ReactNode } from "react";
import { landscape } from "../data/load";
import type { CameraPreset } from "../three/CameraRig";
import type { ColorMode } from "../three/PairColumns";
import { Term } from "./Term";

// The 5-step walkthrough shown when the guided view (2b) opens.
// Each step also sets up the 3D scene so the words and the picture match.
export interface TourStep {
  title: string;
  body: ReactNode;
  mode: ColorMode; // how the landscape is coloured during this step
  camera: CameraPreset;
  focusTopPair?: boolean; // fly to and select the top-scoring pair
  startAgent?: boolean; // make the agent propose its first batch
  highlightApprove?: boolean;
}

const n = landscape.file.pairs.length.toLocaleString();
const pct = ((landscape.hits / landscape.file.pairs.length) * 100).toFixed(1);

export function tourSteps(batch: number, budget: number): TourStep[] {
  return [
    {
      title: "Drug pairs",
      body: <>Each column is one <Term id="pair">drug pair</Term>, tested together on lung cancer cells. {n} pairs in total.</>,
      mode: "dark",
      camera: "focus",
      focusTopPair: true,
    },
    {
      title: "Height",
      body: <>Taller = the drugs worked better together than expected (<Term id="comboScore" />). Below the floor = worse together.</>,
      mode: "dark",
      camera: "low",
    },
    {
      title: "Hits are rare",
      body: <>Only {landscape.hits} pairs ({pct}%) are real <Term id="hit">hits</Term>. They're lit up now.</>,
      mode: "hits",
      camera: "top",
    },
    {
      title: "The agent suggests",
      body: <>The agent suggests {batch} pairs at a time from a <Term id="budget">budget</Term> of {budget} experiments. Its reasons are on the right.</>,
      mode: "replay",
      camera: "angled",
      startAgent: true,
    },
    {
      title: "You decide",
      body: <>Untick any pair you don't want, then test the rest. Only then is the real result shown.</>,
      mode: "replay",
      camera: "angled",
      highlightApprove: true,
    },
  ];
}

interface Props {
  steps: TourStep[];
  index: number;
  onIndex: (i: number) => void;
  onClose: () => void;
}

/** The step card: progress dots, text, Back / Next / Skip. */
export function GuidedTour({ steps, index, onIndex, onClose }: Props) {
  const step = steps[index];
  const last = index === steps.length - 1;
  return (
    <section className="tour" aria-live="polite">
      <div className="tour-top">
        <span className="tour-count">{index + 1} / {steps.length}</span>
        <div className="dots">
          {steps.map((_, i) => (
            <button key={i} className={i === index ? "dot on" : "dot"} aria-label={`Go to step ${i + 1}`} onClick={() => onIndex(i)} />
          ))}
        </div>
      </div>
      <b className="tour-title">{step.title}</b>
      <p>{step.body}</p>
      <div className="tour-actions">
        <button className="link" onClick={onClose}>Skip</button>
        <span className="grow" />
        {index > 0 && <button className="lab-secondary" onClick={() => onIndex(index - 1)}>Back</button>}
        <button className="lab-primary" onClick={() => (last ? onClose() : onIndex(index + 1))}>
          {last ? "Got it" : "Next"}
        </button>
      </div>
    </section>
  );
}
