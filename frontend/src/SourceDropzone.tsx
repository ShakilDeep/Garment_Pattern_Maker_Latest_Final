import {useId, useRef} from 'react';
import {Upload} from 'lucide-react';

type Doc = {id: string; filename: string};
type Props = {
  upload: (file: File, replace?: boolean) => void;
  busy: boolean;
  documents: Doc[];
  replaceSource: boolean;
  setReplaceSource: (v: boolean) => void;
};

/**
 * Facade pattern: Browse label is the face; a transparent file input overlays it.
 * Off-screen / clipped file inputs do not open the OS picker when activated via label.
 */
export default function SourceDropzone({upload, busy, documents, replaceSource, setReplaceSource}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();

  function pick(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    upload(file, replaceSource);
    if (inputRef.current) inputRef.current.value = '';
  }

  return (
    <div
      className="dropzone"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        pick(e.dataTransfer.files);
      }}
    >
      <Upload />
      <strong>Drop your workbook or tech pack</strong>
      <span>XLSX or PDF · up to 10 MB</span>
      <label className="dropzone-replace">
        <input
          type="checkbox"
          checked={replaceSource}
          onChange={(e) => setReplaceSource(e.target.checked)}
        />
        Replace current source and retain its version
      </label>
      <label
        className={`primary browse-files${busy ? ' is-disabled' : ''}`}
        aria-disabled={busy || undefined}
      >
        <span className="browse-files-label">Browse files</span>
        <input
          ref={inputRef}
          id={inputId}
          className="browse-files-input"
          aria-label="Browse files"
          type="file"
          accept=".xlsx,.pdf,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          disabled={busy}
          onChange={(e) => pick(e.target.files)}
        />
      </label>
      {documents.map((d) => (
        <small key={d.id}>{d.filename}</small>
      ))}
    </div>
  );
}
