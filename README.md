# QDTL2 — Barcelona Mobility Control Room (Refactored Base)

This repository is a refactored base for a hybrid classical–quantum urban mobility control room focused on Barcelona.

## What is included

- A **modular package layout** under `src/mobility_os/`
- A **compatibility wrapper** `mobility_runtime.py`
- A **Streamlit control room** entrypoint in `app.py`
- Scenario libraries under `data/scenarios/`
- Hotspot catalogue under `data/hotspots/`
- Basic **tests** for scenario loading, runtime stepping and routing

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Structure

```text
qdtl2/
├─ app.py
├─ mobility_runtime.py
├─ pyproject.toml
├─ requirements.txt
├─ data/
│  ├─ hotspots/
│  └─ scenarios/
├─ src/
│  └─ mobility_os/
│     ├─ domain/
│     ├─ io/
│     ├─ scenarios/
│     ├─ solvers/
│     ├─ orchestration/
│     ├─ runtime/
│     └─ ui/
└─ tests/
```

## Notes

This package preserves the original project intent and core concepts:
- synthetic mobility twins
- hybrid route selection
- fallback-to-classical logic
- scenario-driven execution

The UI has been re-mounted around the new modular architecture rather than porting every original visual element one-for-one.
