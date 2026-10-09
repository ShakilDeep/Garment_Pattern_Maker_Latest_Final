import {useState} from 'react';

const units = [['cm', 'Centimetres (cm)'], ['mm', 'Millimetres (mm)'], ['inch', 'Inches (in)']];

type Props = {disabled: boolean; download: (kind: string, unit: string) => void};

/** AutoCAD DXF at 1:1 in the chosen unit, and DXF-AAMA/ASTM (R12) for Optitex: metric files are mm. */
export default function DxfExport({disabled, download}: Props) {
  const [unit, setUnit] = useState('cm');
  return <div className="actions dxf-export">
    <select aria-label="DXF unit" value={unit} onChange={e => setUnit(e.target.value)}>
      {units.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
    </select>
    <button className="primary" disabled={disabled} onClick={() => download('dxf', unit)}>Download DXF (AutoCAD)</button>
    <button disabled={disabled} onClick={() => download('dxf-aama', unit === 'inch' ? 'inch' : 'mm')}>
      Download DXF-AAMA (Optitex)
    </button>
    <small>DXF-AAMA metric files are in mm. Optitex import is not yet confirmed.</small>
  </div>;
}
