# Research notes

- static site search avoids any backend, so the whole feature is two files: index and script
- a prebuilt Lunr index for 500 documents is roughly 80 KB gzipped
- Debounce input at 150ms to keep the UI responsive on mobile keyboards?
- highlight matched terms with <mark> so users can verify relevance instantly
- q: How large can the index get before load time hurts?
- for large corpora, split the index per section and fetch on demand
