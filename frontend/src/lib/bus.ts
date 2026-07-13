// Lightweight, typed cross-component event bus.
//
// The menu bar lives in the root layout while the page owns the repo/query
// state, so they can't share React state directly. Menu actions that need to
// touch page state talk to it through these window events instead.

export type BusEvents = {
  "clear-query": undefined;
  "reset-session": undefined;
};

export function emit<K extends keyof BusEvents>(type: K, detail?: BusEvents[K]) {
  window.dispatchEvent(new CustomEvent(`codecomp:${type}`, { detail }));
}

export function on<K extends keyof BusEvents>(
  type: K,
  handler: (detail: BusEvents[K]) => void,
): () => void {
  const listener = (e: Event) => handler((e as CustomEvent).detail);
  window.addEventListener(`codecomp:${type}`, listener);
  return () => window.removeEventListener(`codecomp:${type}`, listener);
}
