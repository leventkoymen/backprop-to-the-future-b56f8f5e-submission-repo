import { Html } from "@react-three/drei";
import type { ComponentProps } from "react";

// All 3D-anchored HTML labels render into ONE stable overlay div (set in App).
// Without a fixed portal, drei's Html can throw "removeChild" when a scene unmounts.
export const labelPortal = { current: null as unknown as HTMLElement };

export function Label(props: ComponentProps<typeof Html>) {
  return <Html portal={labelPortal} zIndexRange={[5, 0]} {...props} />;
}
