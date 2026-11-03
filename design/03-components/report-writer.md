# Report Writer

**Responsibility:** render metrics, findings, and (optional) coaching into a Markdown file.

- Pure templating; no analysis logic.
- Layout defined in [report-format.md](../04-data/report-format.md).
- Writes `<name>.md` and `<name>.findings.json` (the `AnalysisResult`, see [schemas](../04-data/schemas.md)) side by side. Default `<name>` is the replay file stem in the current directory; `-o` overrides.
- **Finding text:** one template per finding type, filled from `evidence`. Second person ("you") is used only for the focus player; everyone else is in the third person. Findings JSON never contains prose.
- Output is byte-stable for the same input (sorted keys, fixed number formatting), so fixtures can be diff-tested.
- Charts (Phase 1): simple text tables. Phase 4: images or interactive charts in the GUI.
