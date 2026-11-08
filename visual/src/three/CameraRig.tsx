import { CameraControls } from "@react-three/drei";
import { useEffect, useRef } from "react";

export type CameraPreset = "top" | "angled" | "low" | "focus" | "dose";
export interface CameraCommand {
  preset: CameraPreset;
  target?: [number, number, number]; // for "focus"
  nonce: number; // bump to re-trigger the same preset
}

/** Smooth camera moves between presets (drei CameraControls). Drag/scroll still work. */
export function CameraRig({ cmd }: { cmd: CameraCommand }) {
  const ref = useRef<CameraControls>(null);

  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const t = cmd.target ?? [0, 0, 0];
    switch (cmd.preset) {
      case "top":
        c.setLookAt(0, 165, 0.01, 0, 0, 0, true);
        break;
      case "angled":
        c.setLookAt(95, 75, 115, 0, 0, 0, true);
        break;
      case "low":
        c.setLookAt(-120, 22, 70, 0, 8, 0, true);
        break;
      case "dose":
        c.setLookAt(78, 52, 98, 0, 0, 0, true);
        break;
      case "focus":
        c.setLookAt(t[0] + 22, t[1] + 26, t[2] + 30, t[0], t[1], t[2], true);
        break;
    }
  }, [cmd]);

  return <CameraControls ref={ref} makeDefault smoothTime={0.6} maxDistance={320} minDistance={8} />;
}
