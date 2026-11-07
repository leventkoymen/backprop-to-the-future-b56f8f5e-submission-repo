# LungPair

An audited, human-approved discovery loop for choosing which lung cancer drug combinations a lab should screen next, built on measured NCI-ALMANAC results.

> Replay of measured NCI-ALMANAC results (non-small cell lung cancer, 9 cell lines). Not predictions. No patient data.

## Repository layout

```
data/      shared, read-only inputs (starter data, agent run logs, the log format)
visual/    3D pitch visual (React + TypeScript + Vite + React Three Fiber)
```

## Run the 3D visual

Needs Node 22 (see `visual/.nvmrc`).

```bash
cd visual
npm install        # first time only
npm run dev        # open the printed localhost URL
```

Offline build for the pitch laptop: `npm run build`, then double-click `visual/dist/index.html` (everything, including the data, is inside that one file).

Presenter keys: `1` `2` `3` switch scenes · `Space` next round / approve · `R` reset · `H` light up hits · `T` `A` `L` `F` camera.

## Adding or updating data

| You want to… | Do this |
|---|---|
| Show a new agent run | Save it as `data/runs/<name>.jsonl` in the format in `data/schema/event-log.md`, then restart `npm run dev`. It appears in the Run dropdown. |
| Update scores / hits / tiers | Replace `data/starter/pairs_3d.json` (same structure; an optional `"tier": "T1"…"T4"` per pair turns on "Colour by tier"). |
| Rebuild the labelled demo log | `cd visual && npm run demo-log` |

Malformed log lines are shown as an error in the Scene B panel, never silently dropped.

### After every `git pull`

The frontend (`visual/`) reads files produced by the backend (`agent/` → `data/`). Run:

```bash
cd visual && npm run check-data
```

It validates every data file against `visual/src/data/schemas.ts` and names any renamed, missing or retyped field. `npm run build` runs it automatically, so a structure change can't slip into a build. Format changes are agreed in the team group first and recorded in `data/schema/event-log.md`.

## Data and credits

See `data/README.md`. NCI DTP NCI-ALMANAC (ComboDrugGrowth_Nov2017). Built with three.js, React Three Fiber and drei (MIT).
