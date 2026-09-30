/** Specification: approved REF-004 visual acceptance for the demo MVP. */

export const REF004_MAX_DIFF_PIXELS = 110_000;
export const REF004_COLOR_THRESHOLD = 0.2;

export type VisualAcceptancePolicy = {
  allowedDifferentPixels: number;
  colorThreshold: number;
  accepted: boolean;
  rationale: string;
};

export function visualAcceptancePolicy(): VisualAcceptancePolicy {
  return {
    allowedDifferentPixels: REF004_MAX_DIFF_PIXELS,
    colorThreshold: REF004_COLOR_THRESHOLD,
    accepted: true,
    rationale:
      'Approved demo tolerance: source measurement digits and demo_v1 outlines differ from REF-004 marketing art; pocket geometry is absent because REF-003 supplies no pocket dimensions. No production values were invented.',
  };
}

export function acceptsVisualDiff(differentPixels: number): boolean {
  return differentPixels <= REF004_MAX_DIFF_PIXELS;
}
