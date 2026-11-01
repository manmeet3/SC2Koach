# Report Writer

**Responsibility:** render metrics, findings, and (optional) coaching into a Markdown file.

- Pure templating; no analysis logic.
- Layout defined in [report-format.md](../04-data/report-format.md).
- Writes `<name>.md` and `<name>.findings.json` side by side.
- Charts (Phase 1): simple text tables. Phase 4: images or interactive charts in the GUI.
