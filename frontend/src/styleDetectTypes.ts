/** Style detection (T132): the server's fixed option table, a stored proposal and the user's choice. */
export type OptionSpec = {id: string; label: string; families: string[]; choices: string[]; note: string};
export type OptionGuess = {id: string; value: string; confidence: number};
export type StyleProposal = {garment: OptionGuess; fit: OptionGuess; options: OptionGuess[]; provider: string;
  model: string; prompt_version: string};
export type StyleDetection = {proposal: StyleProposal; source_sha256: string; page: number; at: string};
export type StyleChoices = {garment: string; fit: string; options: Record<string, string>};
export type StoredStyleChoices = StyleChoices & {source: string; at: string};
export const UNKNOWN = 'unknown';

/** Option ids shown for a garment: garment and fit, then the family's own options. */
export function visibleSpecs(specs: OptionSpec[], garment: string): OptionSpec[] {
  return specs.filter((spec) => spec.id === 'garment' || spec.id === 'fit' || garment === UNKNOWN
    || spec.families.includes(garment));
}

/** Flat id → value map from a proposal (every guess, including garment and fit). */
export function proposalValues(proposal: StyleProposal | undefined): Record<string, OptionGuess> {
  if (!proposal) return {};
  return Object.fromEntries([proposal.garment, proposal.fit, ...proposal.options].map((g) => [g.id, g]));
}
