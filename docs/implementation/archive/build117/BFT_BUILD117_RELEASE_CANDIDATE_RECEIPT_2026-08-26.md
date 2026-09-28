# BFT Build 117 Release-Candidate Receipt

**Receipt ID:** BFT-2.1.117-RC1-2026-08-26  
**Prepared by:** Paul, Lead Developer / Lead Analyst  
**Date:** 2026-08-26  
**Status:** Technically verified; controlled release handoff pending

## Candidate identity

- Candidate archive: `out/build117_release_candidate/INSTALL_BUNDLETOOL_v2_1_117_governed_ingress_and_workflow_RC1.zip`
- Candidate archive SHA-256: `967aa62f6298ceacbdf310ce603c54f15e0c0a39122fc039c5ce0e511e0b6695`
- Installer: `INSTALL_BUNDLETOOL_v2_1_117_governed_ingress_and_workflow.bat`
- Installer SHA-256: `b087fecbe1cea589b4539c944712ae06bb12cdf3a3573000abc25ee20d3be432`
- Delivery manifest: 74 entries; SHA-256 `6ad001fd02825b089613a5001793034c32898c4848c9fd3f6b3c740fffc93017`
- Delivery markers: 73 entries; SHA-256 `0ba2653611be3ce93018e370bf450aec4016c3e2fe8c204ff4a1759afb89362f`
- Proposed manifest SHA-256: `4e63bb7ea15414a322a42ae02a20e4779b09ab938342c4da5792f369bde1fe0b`
- Proposed governed-config SHA-256: `5cf84eb590925f681a9d1026b8facf4c7b25e7e8c722384498fd8b3a77b6e69a`

Archive fidelity verification extracted all **79/79** entries and compared each one with the sealed package tree: **zero missing files, zero extra files, and zero hash mismatches**.

## Verification sequence

1. Copied the archived Build 116 baseline into a fresh disposable `bundle_file_tool_v2` directory.
2. Overlaid the candidate installer and `_bundletool_incoming` delivery.
3. Ran the installer with Python 3.11.9, pytest 9.0.2, and coverage 7.13.5.
4. Verified version guard accepted `2.1.116`.
5. Verified staged and installed SHA-256 values for all 74 payload files.
6. Verified 73 text content markers.
7. Verified CLI identity, shared strict ingress, planning facade, cancellation, selection, and config integrity imports.
8. Ran the binding complete suite.
9. Independently re-hashed all 74 installed payload paths after installer success.
10. Confirmed governed config read-only state and success teardown.

## Results

| Evidence | Result |
|---|---|
| Final installer exit | `0` |
| Full suite | `1453 passed, 1 warning in 110.93s` |
| Coverage | `90.82%` (required floor `85%`) |
| Installed payload hash audit | `74 checked, 0 mismatches` |
| Installed identity | `2.1.117` |
| Config protection | Read-only |
| Incoming directory after success | Absent |
| Rollback directory after success | Absent |

The complete final installer transcript is retained at `out/build117_release_candidate/install_test_v4/bundle_file_tool_v2/build117_final_install_run.log`.

## Release decision

Technical candidate gate: **PASS**.

Publication gate: **PENDING** for George's exact-diff approval and an authorized interactive account's commit/tag. No live governed identity mutation, Git index write, commit, tag, or archive publication outside the workspace was performed by automation.
