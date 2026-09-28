# Team Communication — BFT v2.2 Selection Workspace

**Document Ref:** `BFT-ANALYSIS-2026-08-25-02`  
**From:** Paul, Lead Analyst & Collaborative Developer  
**To:** Ringo (Product Owner) · George (Lead Architect) · John (Lead Developer)  
**Date:** 2026-08-25  
**Subject:** Consolidated disposition on the Selection Workspace review, addendum, and implementation gates  
**Responds to:** `ARCH-RULING-2026-08-25-01`, `BFT-DEV-REVIEW-2026-08-25-01`, and `ARCH-RULING-ADDENDUM-2026-08-25-01`  
**Baseline:** BFT v2.1 Build 112, 897 tests, PyThermX 0.5.0  
**Status:** **PROCEED with WP1/WP2; controlled specification revision required before their exit gate**

---

## 1. Executive disposition

George's addendum resolves the six substantive questions John raised and preserves the architecture of the original Selection Workspace specification. I accept all six core rulings and all four operational rulings.

My recommendation is therefore:

1. **John proceeds now** with the performance harness, WP1 (Selection Core), and WP2 (Detectors). There is no remaining basis for an implementation hold.
2. **Ringo approves the viewport model** recommended in the addendum: the default workspace is the decision tree/file list/group-ordering view; serialized bundle text is on demand and bounded; full formatting occurs at Create Bundle.
3. **I issue Specification Revision 1.1** incorporating the addendum, the formal rule-file schema, and the two executable persona fixtures before WP1/WP2 are presented for acceptance.
4. **George confirms four narrow wording/precedence clarifications** in §4 below. They do not justify delaying coding, but they must be closed before precedence and output-purity tests become binding.

This is a controlled refinement, not a redesign. John's review did exactly what a design review should do: it found the places where an apparently sound abstraction would have disagreed with the existing gates or failed its own responsiveness objective.

## 2. Source reconciliation

The three documents form a clear decision chain:

- `ARCH-RULING-2026-08-25-01` ratified the SelectionPlan architecture, seven-layer precedence shape, group sequencing, and WP1/WP2 direction.
- `BFT-DEV-REVIEW-2026-08-25-01` re-verified the original evidence against the live Build 112 tree, measured the unbudgeted formatting cost, and identified six bounded conflicts.
- `ARCH-RULING-ADDENDUM-2026-08-25-01` is the controlling architectural disposition where the earlier ruling and the developer review differ.

The addendum resolves the environment-detector contradiction in favor of **conjunction per family**, splits **hard safety** from overridable governed defaults, requires all known emit-blocking invariants to appear in the plan, and adopts the decision-first viewport. Those outcomes are internally coherent and should be folded into the specification without reopening the larger design.

## 3. Disposition on John's six review items

| Review item | Paul's conclusion | Required specification change |
|---|---|---|
| Environment detector contradiction | **Accepted.** Pruning requires a primary marker plus corroborating layout per environment family. Ambiguous markers are `Unknown`, traversed, and reported. | Replace the flat signature list with conjunctive family definitions and explicit evidence codes. |
| Hard safety vs. governed defaults | **Accepted.** Recursion/archive/self-ingestion hazards belong at Priority 0 and cannot be overridden. Noise-reduction defaults remain overridable. | Split the governed source into safety invariants and ordinary defaults without weakening Layer A/Layer C provenance. |
| Plan vs. create-time gate mismatch | **Accepted with snapshot qualification.** Every known policy or integrity refusal must be `Blocked` during planning. | Define `Included` as eligible under the plan snapshot; preserve create-time revalidation for external changes and I/O faults. |
| Full formatted preview cost | **Accepted.** The current full-text preview is the wrong default representation for a selection workspace. | Make decision/tree/group views primary. Provide a bounded, on-demand output preview; serialize the complete artifact only at Create Bundle. |
| Glob force-include under pruned roots | **Accepted.** Globs operate only on the unpruned index. A literal child path or `--include-root` is required to cross a pruning boundary. | Add scope annotations to the report and define targeted scans as new plan generations. |
| `--exclude` semantic change | **Accepted as an intentional breaking correction.** Additive exclusion is safer and should ship visibly. | Emit a deterministic stderr migration notice and document `--no-default-rules` as the explicit replacement behavior. |

## 4. Four narrow clarifications before WP1/WP3 contracts freeze

These are not reasons to stop WP1 or WP2. They are wording and precedence details that must be made normative before the corresponding tests are declared final.

### 4.1 Ordinary CLI rules need an unambiguous layer

The original ladder places GUI/CLI force overrides at Priority 1 and the opt-in project rule file at Priority 2. The addendum also calls ordinary `--exclude` a Priority 2 session filter. That gives two sources the same layer without defining their order.

**Recommendation:** retain these semantics:

- **Priority 1:** explicit force operations: GUI path/folder override, `--force-include`, `--force-exclude`, and `--include-root`.
- **Priority 2a:** opt-in project rules loaded from `--rules` / `.bft-selection.json`.
- **Priority 2b:** ordinary invocation rules from legacy `--include` and additive `--exclude`, evaluated after 2a so the command line can refine the selected project policy.

Within 2a or 2b, configured order and last-match-wins remain unchanged. This preserves the seven-tier ladder while making the CLI deterministic.

### 4.2 “Included guarantees emission” must be snapshot-scoped

The addendum's intent is correct: a green plan decision must not later fail because BFT hid an already-known integrity rule. It cannot guarantee unconditional emission after a file is deleted, permissions change, the destination fills, or cancellation is requested.

**Recommended invariant:**

> `Included` means the path is eligible for emission under the recorded source snapshot and all known policy/integrity gates. Create Bundle revalidates the snapshot; an external change produces a new `Stale`, `Blocked`, or operational error outcome with an explicit reason before output is claimed complete.

### 4.3 Rule-source digests must not violate transport invariance

I accept S-08. Each active rule source needs a SHA-256 digest and the combined ordered stack needs its own digest. In v2.2 those values belong in `SelectionPlan`, `BundleManifest.metadata`, and the exported selection report.

They must **not** create a new `plain_marker` or `markdown_fence` field in v2.2. The current formatters may carry the metadata in memory while leaving the raw transport grammar byte-compatible. External provenance is supplied by the optional report/sidecar until a v2.3 transport RFC says otherwise.

Digest input should be canonical UTF-8 JSON with sorted object keys, preserved array/rule order, normalized POSIX paths, and no runtime timestamp. Record both per-source digests and one ordered `rule_stack_digest`.

### 4.4 Output purity wording needs correction

The addendum's exemption for `bundle-tool plan` is sound. The phrase “create and bundle commands retain strict zero-stdout purity” is too broad for the current CLI contract: `bundle` emits the bundle artifact to stdout when `--output` is omitted.

**Recommended invariant:**

- `plan`: human or JSON plan data may be written to stdout.
- `bundle` without `--output`: stdout contains bundle bytes/text and nothing else.
- `bundle` with `--output`: stdout is empty.
- Diagnostics, migration notices, progress, warnings, and report locations always go to stderr.

## 5. Product recommendation for Ringo — approve the viewport model

I recommend approval of George's §2.4 viewport model with the following binding behavior:

- The default workspace shows the SelectionPlan: folders, groups, decision list, reasons, overrides, estimated payload size, and approximate token budget.
- A checkbox or group-order change updates decision state and counts immediately. It does not serialize the bundle.
- **Preview Output** is a separate, on-demand tab bounded to the first **10 files or 50 KB of formatted output**, whichever limit is reached first. The truncation boundary is explicit.
- **Create Bundle** performs the only full transport serialization. Existing integrity and cancellation gates remain in force.
- The full preview may be offered later as an explicit background action, but it is not part of the default interaction or the sub-250 ms responsiveness promise.

John's measurements are decisive here: formatting 4,000 files takes approximately 1.1 seconds at p50 and 1.34 seconds at p95 even with zero content reads. A full text preview on every toggle would preserve the old coupling under a new cache.

## 6. Rule-file schema direction for Specification Revision 1.1

The formal JSON Schema will define the following contract for personal presets and opt-in `.bft-selection.json` files:

```json
{
  "schema_version": "1.0",
  "name": "Book + campaign",
  "base_action": "exclude",
  "rules": [
    {
      "id": "manuscript",
      "enabled": true,
      "order": 10,
      "action": "include",
      "match": {"type": "glob", "pattern": "chapters/**/*.md"},
      "group": "manuscript"
    },
    {
      "id": "exports",
      "enabled": true,
      "order": 90,
      "action": "exclude",
      "match": {"type": "glob", "pattern": "exports/**"}
    }
  ],
  "groups": [
    {"id": "manuscript", "label": "Manuscript", "order": 10},
    {"id": "research", "label": "Research", "order": 20},
    {"id": "campaign", "label": "Campaign", "order": 30}
  ]
}
```

Normative constraints:

- User/project rule actions are `include` or `exclude`; `block` is reserved to Priority 0 governed safety.
- Matcher types in v1 are `glob`, `path`, `extension`, `detector`, and `size`.
- Paths and globs are project-relative POSIX strings. Absolute paths, `..` traversal, environment expansion, command execution, and regex are invalid.
- Rule IDs and group IDs are unique within the file. Rule order is explicit and deterministic.
- Unsupported `schema_version` fails loud. Unknown fields are preserved but ignored by v1 evaluation; only documented fields affect selection.
- Project files are never auto-activated. The CLI requires `--rules`; the GUI requires explicit opt-in and displays the active source plus digest.
- A reference to a shipped detector names a registered detector ID; rule files cannot provide executable detector code.

## 7. Reference fixtures Paul will formalize

### 7.1 Application developer fixture

The fixture will include:

- Authored `src/`, `tests/`, configuration, and documentation files.
- `.venv/` and `.venv312/` with `pyvenv.cfg` plus platform interpreter layout: pruned and represented as excluded roots.
- A conda root with `conda-meta/history`: pruned.
- `node_modules/` with parent `package.json`: pruned as a dependency tree.
- An ambiguous subtree containing only `bin/activate`: traversed, indexed, and reported `Unknown` rather than excluded.
- Nested bundle/archive candidates: `Blocked` at plan time.
- A literal child force-include under a pruned root: targeted scan and a new immutable plan generation.
- A force-include glob aimed into a pruned root: no deep scan, zero matches from the pruned subtree, and an explicit scope note.
- `--include-root`: visible un-prune followed by a costed subtree scan.

### 7.2 Writer and marketer fixture

The fixture will include:

- `front-matter/`, `chapters/`, `research/`, `marketing/copy/`, `marketing/social/`, and reference images.
- `exports/`, `archive/`, and video masters excluded by ordinary, overridable rules.
- Manuscript, Research, Campaign, and Reference Images groups with deterministic order.
- One path matching multiple groups to prove single emission and first-primary-group behavior.
- Binary images and video to verify source bytes vs. base64-adjusted estimated payload size.
- Group reorder and exclusion changes that perform zero content reads.
- Expected text and JSON plan snapshots plus a final manifest-order assertion.

## 8. Revised performance and quality gates

| Gate | Binding target |
|---|---|
| `SEL-PERF-001` | One toggle in a 4,000-path plan performs zero unchanged content reads and updates state/counts within 50 ms p95. |
| `SEL-PERF-002` | Initial 4,000-path SelectionPlan becomes available within the measured budget set by John's harness; Tk renders the first usable viewport within 150 ms after plan delivery. |
| `SEL-PERF-003` | Rapid changes inside 250 ms produce one bounded-preview generation; stale generations never update the UI. |
| `SEL-PERF-004` | Bounded Preview Output formats no more than 10 files or 50 KB and reports truncation explicitly. |
| `SEL-PERF-005` | Full serialization occurs only on Create Bundle and remains byte-identical to a cold build for the same plan/profile. |
| `SEL-DET-001` | Conjunctive environment signatures prune before descent; ambiguous single markers are traversed and reported. |
| `SEL-A11Y-001` | The complete model remains programmatically addressable; Tk virtualization affects widgets only; search/filter provide structured assistive navigation. |
| `SEL-GOV-001` | SelectionPlan, BundleManifest metadata, and reports contain per-source and ordered-stack rule digests without changing v2.2 transport syntax. |

For S-09, the UI label should be **Estimated Payload Size**, with source bytes shown separately. Binary files use exact Base64 expansion (`4 * ceil(n / 3)`) rather than a rounded 1.33 multiplier; provenance/header overhead is then added by the selected profile estimator. Token counts must be labeled approximate and name the estimator because tokenization is model-dependent.

## 9. Team actions

### John

- Proceed with the baseline performance harness, WP1, and WP2 under the addendum.
- Model pruned roots explicitly; an expand, explicit child override, or `--include-root` creates a new metadata snapshot and new immutable SelectionPlan rather than mutating the old plan.
- Keep emit-blocking rule evaluation in core and keep GUI/CLI adapters policy-free.
- Use the schema/fixture direction in §§6–7 as the interim contract pending Specification Revision 1.1.

### George

- Confirm the Priority 2a/2b ordering, snapshot-scoped `Included` invariant, non-serialized digest interpretation, and corrected stdout wording in §4.
- Pair with John on state transitions and precedence fixtures as offered.

### Ringo

- Approve the default decision-first workspace and bounded on-demand output preview in §5.
- Confirm that this interaction decision is sufficient to close the short design round and keep WP1/WP2 in motion.

### Paul

- Publish Specification Revision 1.1 with the addendum integrated rather than appended as contradictory text.
- Deliver the formal JSON Schema and both executable persona fixtures before WP1/WP2 acceptance.
- Reconcile the performance gates with John's harness results and maintain a disposition table from each review finding to a test or specification clause.

## 10. Final recommendation

**Proceed.** The Selection Workspace architecture has survived both architectural and implementation review. The addendum closes the material defects John identified, and the remaining four items are narrow contract clarifications—not grounds for delay.

Ringo's viewport approval is the only remaining product decision. My recommendation is to approve it as written in §5. Once confirmed, the design round is closed; Revision 1.1 becomes the acceptance authority while John continues WP1/WP2 implementation in parallel.

---

**Paul**  
Lead Analyst & Collaborative Developer  
`BFT-ANALYSIS-2026-08-25-02`
