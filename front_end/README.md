# FinRAG UI

Vanilla HTML, CSS, and JavaScript interface for the Adaptive RAG financial-report project.

## Run

From the repository root, serve this directory with any static server, for example:

```powershell
python -m http.server 8080 --directory front_end
```

Open `http://localhost:8080`. Pages are linked from the shared sidebar. API modules use `/api` by default and can be configured through `window.FINRAG_API_BASE`.

## Structure

- `pages/`: page entry documents
- `css/`: base, layout, component, and page styles
- `js/`: shared components, page controllers, API clients, and utilities
- `assets/`: logos, icons, and images
