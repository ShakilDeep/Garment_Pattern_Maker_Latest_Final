import {useEffect} from 'react';
import type {Dispatch, SetStateAction} from 'react';

/** Global shortcuts: Ctrl/Cmd+K opens the command palette; Ctrl/Cmd+Z and Shift+Z undo/redo edits. */
export function useKeyboardShortcuts(setDialog: Dispatch<SetStateAction<string>>, history: (direction: string) => void) {
  useEffect(() => {
    const listener = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setDialog('commands'); }
      if ((e.target as HTMLElement).matches('input,textarea,select')) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault(); history(e.shiftKey ? 'redo' : 'undo');
      }
    };
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, [setDialog, history]);
}
