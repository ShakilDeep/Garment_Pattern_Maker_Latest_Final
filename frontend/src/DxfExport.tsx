import {useState} from 'react';

const units = [['cm', 'Centimetres (cm)'], ['mm', 'Millimetres (mm)'], ['inch', 'Inches (in)']];

type Props = {disabled: boolean; download: (kind: string, unit: string) => void};

/** AutoCAD DXF at 1:1 scale; the file's $INSUNITS header carries the chosen unit. */
export default function DxfExport({disabled, download}: Props) {
  const [unit, setUnit] = useState('cm');
  return <div className="actions dxf-export">
    <select aria-label="DXF unit" value={unit} onChange={e => setUnit(e.target.value)}>
      {units.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
    </select>
    <button className="primary" disabled={disabled} onClick={() => download('dxf', unit)}>Download DXF (AutoCAD)</button>
  </div>;
}
