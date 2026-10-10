import {LAYERS, type Layer} from './styleTypes';

const LABELS: Record<Layer, string> = {cut: 'Cut line', sew: 'Sew line', notches: 'Notches', grain: 'Grain', labels: 'Labels'};

type Props = {shown: Set<Layer>; toggle: (layer: Layer) => void};

export default function LayerToggles({shown, toggle}: Props) {
  return (
    <fieldset className="layer-toggles">
      <legend>Layers</legend>
      {LAYERS.map((layer) => (
        <label key={layer}>
          <input type="checkbox" checked={shown.has(layer)} onChange={() => toggle(layer)} />
          {LABELS[layer]}
        </label>
      ))}
    </fieldset>
  );
}
