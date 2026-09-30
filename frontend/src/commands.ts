export type PaletteCommand = {
  id: string;
  label: string;
  page: string;
  hint: string;
  shortcut?: string;
  disabled?: string;
};

type PaletteState = {canGenerate: boolean; hasPattern: boolean};

const CATALOG: Omit<PaletteCommand, 'disabled'>[] = [
  {id: 'dashboard', label: 'Project Dashboard', page: 'Project Dashboard', hint: 'Resume files, blockers, and next step', shortcut: 'G'},
  {id: 'measurements', label: 'Measurements', page: 'Measurements', hint: 'Review workbook values and units'},
  {id: 'requirements', label: 'Requirements', page: 'Requirements', hint: 'Resolve missing and conflicting source items'},
  {id: 'generate', label: 'Generate Pattern', page: 'Generate Pattern', hint: 'Create the current size from confirmed sources'},
  {id: 'studio', label: 'Pattern Studio', page: 'Pattern Studio', hint: 'Inspect pieces, notches, and CAD commands', shortcut: 'F'},
  {id: 'validation', label: 'Validation Center', page: 'Validation Center', hint: 'Open errors, warnings, and corrective actions'},
  {id: 'grading', label: 'Grading', page: 'Grading', hint: 'Regenerate S–3XL from the size table'},
  {id: 'marker', label: 'Marker Nesting', page: 'Marker Nesting', hint: 'Compare utilization only when a prior marker exists'},
  {id: 'export', label: 'Export', page: 'Export', hint: 'Download SVG, PDF, or JSON with demo assumptions'},
];

export function paletteCommands(query: string, state: PaletteState): PaletteCommand[] {
  const needle = query.trim().toLowerCase();
  return CATALOG.filter((row) => `${row.label} ${row.hint}`.toLowerCase().includes(needle)).map((row) => {
    if (row.id === 'generate' && !state.canGenerate) {
      return {...row, disabled: 'Requirements must be resolved before generation'};
    }
    if ((row.id === 'studio' || row.id === 'export') && !state.hasPattern) {
      return {...row, disabled: 'Generate a current pattern first'};
    }
    return row;
  });
}
