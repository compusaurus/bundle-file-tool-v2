# Bundle File Tool Documentation Visibility and Publication Policy

**Document class:** `RESTRICTED_INTERNAL`  
**Status:** Proposed policy for team ratification  
**Last updated:** 2026-08-31  

## 1. Default and labels

Bundle File Tool documentation is **restricted by default**. Repository presence, an index link, an open-source intent, or an author's approval statement does not authorize external distribution.

Only `PUBLIC_APPROVED` documents may be copied to a public repository, website, release package, customer portal, or external communication channel.

| Label | Meaning | External distribution |
|---|---|---|
| `PUBLIC_APPROVED` | Exact version has completed the publication gate | Allowed only for its recorded audience/channel |
| `PUBLIC_CANDIDATE` | Potentially publishable after review | **Not allowed yet** |
| `RESTRICTED_INTERNAL` | Internal architecture, build, quality, governance, review, or operations material | Authorized collaborators only |
| `RESTRICTED_COMMERCIAL` | Unreleased UX, product plans, strategy, market, partner, or roadmap material | Need-to-know business access |
| `RESTRICTED_SECURITY` | Threat, trust, hardening, key, update, incident, or security-test details | Need-to-know engineering/security access |
| `RESTRICTED_CONFIDENTIAL` | Customer, personal, contractual, credential, secret, or incident-specific data | Explicitly authorized recipients and storage only |

## 2. Configurable classification precedence

Future automation should read classification from a review-controlled manifest using this order:

1. exact-file rule;
2. nearest parent-directory rule;
3. project default (`RESTRICTED_INTERNAL`).

If rules conflict, the most restrictive result wins:

```text
RESTRICTED_CONFIDENTIAL > RESTRICTED_SECURITY > RESTRICTED_COMMERCIAL
> RESTRICTED_INTERNAL > PUBLIC_CANDIDATE > PUBLIC_APPROVED
```

Until a machine-readable manifest is ratified, [INDEX.md](INDEX.md) is the classification register. Unknown, missing, malformed, or stale classifications must fail closed as `RESTRICTED_INTERNAL`. Archive status does not reduce sensitivity.

## 3. Initial collection rules

| Document family | Default classification |
|---|---|
| Architecture, ADRs, rulings, ConfigEditor contracts, implementation and team reviews | `RESTRICTED_INTERNAL` |
| Unreleased product/UX specifications and renders | `RESTRICTED_COMMERCIAL` |
| Build evidence, repair reports, QC databases, generated workspaces and internal provenance | `RESTRICTED_INTERNAL` |
| Threat, credential, key, incident, exploit or hardening details, if introduced | `RESTRICTED_SECURITY` or `RESTRICTED_CONFIDENTIAL` |
| General project README, user guide, support matrix and reusable VCS specification | `PUBLIC_CANDIDATE` until approved |
| Credentials, private keys, customer content and incident-specific evidence | `RESTRICTED_CONFIDENTIAL`; do not store in ordinary docs |

## 4. Publication gate

A candidate becomes `PUBLIC_APPROVED` only after recording its exact path and hash/version, audience/channel, owner, product approval, security review, legal/privacy/IP review where applicable, secret/PII scan, internal-path and metadata review, accuracy/supportability review, effective date, and review/expiry date.

Public export must:

1. select only exact `PUBLIC_APPROVED` versions from [PUBLIC_INDEX.md](PUBLIC_INDEX.md);
2. copy them to a clean staging area;
3. exclude archives, temporary/lock files, generated evidence, symlinks, restricted backlinks, internal paths, comments, document properties, and embedded source objects;
4. scan for secrets, personal/customer data, and unsafe attachments;
5. verify links, file hashes, and rendered output;
6. produce an export manifest and retain approval evidence; and
7. stop on unknown classifications, broken controls, or stale approvals.

Do not publish the internal `docs/` tree wholesale.

## 5. Required metadata and resilience

New or materially revised documents should record title, stable ID, lifecycle, visibility, owner, last-updated date, supersession, and approved audience when public. Binary documents may carry this metadata in the master index until migrated.

Classification may be tightened immediately. Relaxing it requires the publication gate. If restricted content is exposed, stop distribution, preserve evidence, notify ownership/security, assess scope, rotate affected secrets, and issue or withdraw corrected versions. Public approvals should expire or be reviewed after material product changes.

## 6. Current public standing

No Bundle File Tool document is `PUBLIC_APPROVED` as of 2026-08-31. Candidate names remain only in the restricted master index until approval.

