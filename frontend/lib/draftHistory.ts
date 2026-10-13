/**
 * Undo/redo for the open draft. Each edit records the draft as it was; edits closer together than GROUP_MS (typing,
 * dragging) become one step. Subscribe with useSyncExternalStore(history.subscribe, history.flags) to show whether
 * undo/redo are possible.
 */
const GROUP_MS = 700;
const LIMIT = 100;

export class DraftHistory<T> {
  private past: T[] = [];
  private future: T[] = [];
  private lastAt = 0;
  private listeners = new Set<() => void>();
  private state = "00"; // canUndo, canRedo

  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  /** "10" = can undo, can't redo, and so on (a string so React can compare snapshots). */
  flags = () => this.state;

  /** The draft is about to change from `before`. Safe to call twice for one change (React may re-run updaters). */
  record(before: T) {
    const now = Date.now();
    if (now - this.lastAt > GROUP_MS && this.past.at(-1) !== before) {
      this.past.push(before);
      if (this.past.length > LIMIT) this.past.shift();
    }
    this.lastAt = now;
    this.future = [];
    this.changed();
  }

  /** The draft to go back to (and remember `current` for redo), or null. */
  undo(current: T): T | null {
    const before = this.past.pop();
    if (before === undefined) return null;
    this.future.push(current);
    this.lastAt = 0;
    this.changed();
    return before;
  }

  redo(current: T): T | null {
    const after = this.future.pop();
    if (after === undefined) return null;
    this.past.push(current);
    this.lastAt = 0;
    this.changed();
    return after;
  }

  /** End the current group: the next edit is a step of its own (called when a drag ends). */
  seal() {
    this.lastAt = 0;
  }

  reset() {
    this.past = [];
    this.future = [];
    this.lastAt = 0;
    this.changed();
  }

  private changed() {
    const next = `${this.past.length ? 1 : 0}${this.future.length ? 1 : 0}`;
    if (next === this.state) return;
    this.state = next;
    // record() runs inside a state update; tell subscribers afterwards, not while React is rendering
    queueMicrotask(() => this.listeners.forEach((l) => l()));
  }
}
