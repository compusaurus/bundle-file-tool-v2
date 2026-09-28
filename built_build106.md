# BFT v2.1 Build 106 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_106_service_facade.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-18
**Authority:** Build 100 mandatory scope **D-002** (one shared `BundleToolService` with CLI,
Tkinter and Web adapters), ratified by George. Sequenced by Paul
(`BFT-ANALYSIS-2026-08-18-03`): *"Once those gates pass, Build 105 can be accepted as the
stabilized base for the service-facade and therm integration work."*

---

## 1. What this build delivers

Paul's work-package table recorded **WP2 as not started** and **WP5 as not started**: the CLI
constructs the parser, writer, creator and registry directly, so every interface re-derives
the same orchestration and any two of them can drift.

Build 106 introduces the facade and the progress contract that sits on its boundary. It also
closes the specific gap Paul identified as blocking therm:

> BFT cannot yet supply a rising discovery count. `BundleCreator.discover_files()` returns a
> completed list and exposes no callback or iterator during its recursive walk.

| Component | File | Purpose |
|---|---|---|
| Progress event | `src/core/progress.py` | `OperationProgress` — serializable, renderer-agnostic |
| Service facade | `src/core/service.py` | `BundleToolService` — bundle, extract, validate |
| Discovery events | `src/core/writer.py` | rising indeterminate count during the walk |

**Deliberately out of scope:** migrating the CLI onto the facade. That is WP5 and ships
separately, so the two changes can be reviewed and rolled back independently. The CLI is
unchanged by this build.

## 2. The progress contract

Implemented exactly as Paul specified — operation, phase, mode, current, total, unit,
message — plus a derived `percent`, with two rules that are load-bearing rather than
decorative:

**The core imports no renderer.** `progress.py` and `service.py` import no toolkit, no
therm, no Flask, and the service contains no `print`. Tests assert this by reading the
source, because it is the property that lets one operation feed three interfaces. Paul's
instruction was explicit: *do not make the shared service return CLI renderer objects.*

**A sink can never break the operation.** `emit()` swallows sink failures, for the same
reason the Build 105 drift reporter does. A test drives discovery with a sink that raises on
every event and asserts all files are still found.

**`percent` is `None` when unknown, never `0.0`.** A renderer handed zero draws an empty bar
and tells the user nothing has happened, when the truth is that we cannot know. This mirrors
the decision George ratified for therm (R-THM-01/02).

### The discovery handoff

```
discover  0 files   indeterminate
discover  1 files   indeterminate
discover  2 files   indeterminate
discover  3 files   indeterminate
discover  4 of 4    determinate     <- count known only now
read      1 of 4    determinate
```

That transition is precisely what therm 0.2.0's ratified `promote(total, *, current=0)`
consumes: a rising count with no total, then a total once discovery finishes.

## 3. Verified against the real therm package

The contract was exercised against the installed therm 0.1.0 wheel, not a stub. A fifteen-line
adapter in the *caller* maps events to `ThermometerCore` and `CLIThermometer`:

```
therm version: 0.1.0
  [indeterminate] discover: 0 files
  [indeterminate] discover: 1 files
  ...
  therm rendered the determinate phases:
    [########################################] |  100.0% | 4/4 | discover
```

BFT gained no dependency on therm to achieve this, which is the point — the adapter lives
with the consumer.

## 4. Safety gates moved inside the service

The integrity gate and extraction reconciliation now run **inside** the facade, so no
adapter can bypass them by constructing the pieces itself. That is the failure mode a facade
exists to prevent, and it is tested: bundling a directory containing an embedded bundle
raises `ValidationError` through the service and writes nothing.

## 5. QA evidence

| Gate | Result |
|---|---|
| Whole suite | **622 passed, 0 failed** (Build 105 shipped 592) |
| Coverage | **90.09%** against the 85% floor |
| Byte-compile | clean |
| therm integration | event stream drives therm 0.1.0 end to end |
| Round trip through the facade | both profiles, bundle → extract → compare |

New tests: **30** (592 → 622).

| File | Tests | Covers |
|---|---:|---|
| `tests/unit/test_progress_contract.py` | 14 | event semantics, serialization, immutability, sink safety, rising discovery count, renderer-agnosticism |
| `tests/integration/test_service_facade.py` | 16 | round trip on both profiles, include/exclude, integrity gate, reconciliation, dry run, phase sequences, no interface leakage |

## 6. Payload SHA256 table (14 files)

| SHA256 | Bytes | Path |
|---|---:|---|
| `b2f72e08e6b993b7abf8f08e4503e9bd6bd3aa3167583605e180f74f52191d89` | 5859 | `src/core/progress.py` |
| `d0c82ea788c989966cf02e561a1bad1bc53a9e78fe8daa9a6f0346772a26a622` | 12899 | `src/core/service.py` |
| `7230acd184414c398400164582cdde9125ac8e62c75c0c813cd6a9e17ad6d718` | 35942 | `src/core/writer.py` |
| `e564296a5d51b8b3fe8a918d6e1accf9f3d39746a62f5241d5e8454642c1d580` | 628 | `src/core/version.py` |
| `923f502d649b52d9de1b4150fde56ac0a02defea0bf7ba274b5265ddd2ca8e4d` | 2050 | `src/core/module_ids.py` |
| `37b29d0fb39a2ef85b5185f18d5c8365f853713958f4bdcdcb6ffb460a8a3616` | 37217 | `src/database/schema_ids.py` |
| `fe11e0d9eb7a57b508318b7e0d51006a9c19843a7e35bd8b42a9c9ad5f4f0dbb` | 8 | `VERSION.txt` |
| `4f0261a876e293b95b1339db184454b0aa2fed1f0967365432fb895502c8aa3f` | 2132 | `pyproject.toml` |
| `93acf9da890f061ae4f223c1af5a055945c7bb5f55513b64caf593eaf9a35023` | 1473 | `bundle_config.json` |
| `65f99f261090cb67c29cb29c01f0122c30b880b23a33d895fce47b69a8d111bb` | 2617 | `.pyprojectmgr/project_spec.json` |
| `f4e908da7e5aa7dcaf5b981b78b12bcfccec7003ca3f61ec547d3f19c7b52480` | 15837 | `.pyprojectmgr/project_manifest.json` |
| `dfda2a16c9d845dceb23e3e6662c94cfd671f3ec4fc5641a526f401e8bb0c9fc` | 6868 | `tests/unit/test_progress_contract.py` |
| `6ca7b7355324f95fea64c1c769745d0cdc9fa09c7addf6c7c7a1c01920fc64c8` | 8878 | `tests/integration/test_service_facade.py` |
| `df186c87276b7340e15021e674b4b8228224d2137e245ae7926c244213b82c41` | 3923 | `tests/unit/test_release_contract.py` |

## 7. Skeleton-diff proof

```
helper block SHA256 : 53948714915169d1309e5157030ee437231ac408e576483dbc427f164dfa677e
installer SHA256    : 0e76b40fb2db67ea486da0ca230a40c8cecc206bfd35edd8c36d89180487649b
```

Sourced from the canonical template restored in Build 105 and verified against the recorded
hash. Pure ASCII, CRLF, no marker string contains `( ) & | < > ^`.

## 8. What George should rule on

The **shape of `OperationProgress` is Paul's recommendation, not yet a ratified contract.**
Everything else here follows D-002. Specifically:

1. The field set — operation, phase, mode, current, total, unit, message, plus derived
   `percent`. Adding a field later is additive; changing one is not.
2. `percent` returning `Optional[float]`, consistent with R-THM-01's decision for therm.
3. The sink signature `Callable[[OperationProgress], None]` and its never-raise guarantee.
4. Whether the phase vocabulary (`discover`, `read`, `format`, `parse`, `write`, `complete`)
   should be frozen now, since a Web adapter will key presentation off it.

I have shipped it rather than holding, because Ringo asked for forward motion and the
contract is additive — no existing call site changed, and `progress=None` is the default
everywhere. If George rules differently, the change is confined to two new modules.

## 9. Work-package status after this build

Against Paul's table:

| WP | Before | After |
|---|---|---|
| WP2 service facade | Not started | **Delivered** — facade exists, gates inside, CLI migration pending |
| WP5 CLI adapter | Not started | Unchanged — next |
| WP6 Tkinter adapter | Partial | Unchanged; the event contract it needs now exists |
| WP7 Web adapter | Not started | Unchanged; events serialize for streaming or polling |

## 10. Open items

1. **WP5** — migrate the CLI onto the facade. The obvious next BFT build.
2. **George's ruling** on the progress contract, §8.
3. **therm 0.2.0** can now be built against a real event source.
4. UI coverage debt, `BFT-WP0-QC-001`, and the 3.12 environment gap all stand unchanged.
