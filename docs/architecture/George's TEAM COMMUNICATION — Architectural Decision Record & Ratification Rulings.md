# **TEAM COMMUNICATION — Architectural Decision Record & Ratification Rulings**

**Record ID:** ARCH-RULING-2026-08-18-01  
**From:** George, Lead Architect  
**To:** Ringo, Product Owner  
**CC:** Paul, Lead Analyst; John, Lead Developer  
**Date:** August 18, 2026  
**Subject:** Architectural Decisions and Technical Specifications on BFT Configuration Ownership (Build 104), pyprojectmgr Governed Manifest Identity, therm Promotion & Clock Contracts, and Delivery Stager Hardening  
**Status:** **RATIFIED & AUTHORIZED FOR EXECUTION**  
**Document Link:** [TEAM\_George\_Config\_Ownership\_and\_Architectural\_Rulings\_2026-08-18.md](https://docs.google.com/document/d/1-dDqmrFHctuIbeGO9SERR93Yfat1iZuWLZ-0uuhDL2k/edit)

## **1\. Executive Summary & Architectural Disposition**

I have reviewed John’s memorandum (*Memo to George — required architectural rulings*, 2026-08-18).  
John has accurately identified the root cause behind the recurring regressions in **Bundle File Tool (BFT)** and **pyprojectmgr**: the **dual-role anti-pattern**, where an immutable, hash-verified delivery artifact or project baseline is simultaneously treated as a runtime scratchpad or re-initialized with destructive amnesia.  
Under our governance framework, **governed baseline contracts must remain immutable at runtime**. Transient UI states, window coordinates, and dynamic session caches must never share a write-path or storage file with ratified delivery payloads or project identity definitions.

### **Summary of Architectural Rulings:**

> 1. **Item 1A · BFT Configuration Ownership (R-BFT-01):** **Option A (File Split) is RATIFIED**. Governed safety defaults and version metadata remain in bundle\_config.json (strictly read-only at runtime). User convenience state is relocated to %LOCALAPPDATA%\\BundleFileTool\\user\_state.json. Authorized as the core architecture for **BFT Build 104**.  
> 2. **Item 1B · pyprojectmgr Governed Manifest Identity (R-PPM-01):** **RATIFIED**. create\_baseline\_manifest() must preserve existing governed identity (project\_meta.\*, meta.\*, and db\_uid) across re-baselines. A destructive wipe/UUID regeneration requires the explicit \--force-new-identity flag.  
> 3. **Item 2 · therm Promotion Contract (R-THM-01):** **CONFIRMED & RATIFIED**. Promotion from indeterminate to determinate mode is strictly one-way (raises ValueError on repeated calls); current \> total clamps to total; promote(0) raises ValueError.  
> 4. **Item 3 · therm Elapsed Time Ownership & Clock Injection (R-THM-02):** **CONFIRMED & RATIFIED**. Elapsed time and throughput telemetry belong strictly to ThermometerCore, driven by an injected monotonic clock (clock: Callable\[\[\], float\] \= time.monotonic). No start() method is added.  
> 5. **Item 4 · Delivery Standard Dual Version/Build Tracking (R-DEL-01):** **APPROVED**. Authorized the ratified stager skeleton to ingest both VERSION.txt (SemVer) and BUILD.txt (monotonic build integer).  
> 6. **Item 5 · pyprojectmgr Vendored therm Retirement Sequencing (R-PPM-02):** **RATIFIED**. Decoupled into a two-stage process: package standalone therm 0.1.0 wheel in Phase 1, then execute a zero-behavior-change drop-in replacement in a dedicated pyprojectmgr maintenance build prior to rolling out therm 0.2.0.  
> 7. **Item 6 · Path Rule Widening & Stager Option Parsing (R-BFT-02 & R-DEL-02):** **APPROVED**. \_BUNDLE\_ARTIFACT\_RE is widened to capture singular bundle artifacts and self-build manifests. PREP\_AND\_STAGE\_BFT.bat argument parsing is corrected with hoisted %\~dp0 resolution.

## **2\. Item 1A: BFT Configuration Ownership & Build 104 Architecture**

### **2.1 Evaluation of Proposed Options**

| Option | Description | Evaluation & Architectural Disposition |
| :---- | :---- | :---- |
| **Option A** | **Split the files.** Governed defaults stay in bundle\_config.json, read-only at runtime. User state moves to a separate store owned by the GUI. | **APPROVED & RATIFIED.** Eliminates the defect at its root. Separates immutable delivery payload from mutable session scratchpad. Restores cryptographic hash stability and release contract integrity. |
| **Option B** | **Allowlist on save.** save() writes only keys designated user-writable and preserves governed sections from disk. | **REJECTED.** Leaves the delivery payload mutable at runtime. Susceptible to formatting drift, timestamp changes, and hash invalidation by GUI actions. |
| **Option C** | **Merge on save.** Re-read from disk, apply only changed user-state keys, write back. | **REJECTED.** Same fundamental architectural flaw as Option B. Governed release artifacts must not be runtime write targets. |

### **2.2 Formal Ruling (R-BFT-01) & Technical Specification**

> 1. **Storage Topology & File Location:**  
   * **Governed Delivery Payload (bundle\_config.json):** Installed in the application package root. Opened strictly in read-only mode (r, UTF-8). Contains immutable ratified D-005 security defaults (safety.allow\_globs, deny rules, path normalization rules) and application version.  
   * **User State Store (user\_state.json):** Stored in the user's local application data directory:  
     * **Windows:** %LOCALAPPDATA%\\BundleFileTool\\user\_state.json  
     * **POSIX / macOS:** \~/.config/bundle\_file\_tool/user\_state.json (or $XDG\_CONFIG\_HOME/bundle\_file\_tool/user\_state.json)  
     * **Portable Mode Override:** If environment variable BFT\_PORTABLE=1 is set, user state is read from .bft\_user\_state.json in the working directory (which must be added to .gitignore and BFT bundle exclusions).  
   * **Prohibition of Project-Root User State:** User state must **never** be written to the application root directory. Writing to the project root causes self-bundling corruption, dirty git working trees, and installer signature invalidation.  
> 2. **Core Class Architecture:**  
   * Implement UserStateStore in src/core/user\_state.py to manage last\_source\_dir, last\_bundle\_save\_dir, window\_geometry, and first\_launch.  
   * ConfigManager in src/core/config.py is stripped of runtime file mutations. Its save() method must be deprecated; calling it on governed configurations will raise ReadOnlyConfigError.  
   * UI call sites (src/ui/bundle\_frame.py:311 and src/ui/main\_window.py:452) are refactored to call UserStateStore.save().  
> 3. **Migration & First-Launch Protocol:**  
   * On startup, if user\_state.json does not exist:  
     * Check if existing bundle\_config.json contains user convenience keys.  
     * If found, seed user\_state.json with those values.  
     * If not, initialize user\_state.json with safe defaults (window\_geometry \= "1000x700", first\_launch \= true, etc.).  
   * bundle\_config.json is never mutated during this migration.  
> 4. **Test Suite Updates:**  
   * Refactor test\_config.py, test\_config\_migration.py, and test\_migration.py to assert that ConfigManager loads governed settings immutably and that user-state persistence exercises UserStateStore.  
   * Ensure test\_release\_contract.py validates the pristine state of bundle\_config.json without interference from GUI execution.

## **3\. Item 1B: pyprojectmgr Governed Manifest Identity & Re-Baseline Discipline**

### **3.1 Defect Analysis**

The behavior in src/core/project\_init.py:312-325 represents a destructive ratchet anti-pattern. While creating a timestamped backup (project\_manifest\_backup\_\<ts\>.json) preserves historical bytes on disk, the active manifest is wiped and replaced with hardcoded "version": "0.1.0" and a newly generated db\_uid \= uuid.uuid4().  
This amnesia clobbers ratified project identities (e.g., reverting BFT 2.1.103 to 0.1.0), invalidates MANIFEST\_HASH constants across module\_ids.py and schema\_ids.py, and causes cascading release contract failures. It is directly linked to PPM-DEFECT-002 and explains why BFT-WP0-QC-001 has repeatedly drifted.

### **3.2 Formal Ruling (R-PPM-01) & Specification**

> 1. **Idempotent Re-Baselining:**  
   * When create\_baseline\_manifest() is executed against an existing project with a manifest:  
     1. Create the timestamped backup (retaining defense in depth).  
     2. Load and parse the existing project\_manifest.json.  
     3. Carry forward all governed project identity fields into the new baseline:  
        * project\_meta.version, full\_name, maintainer, license, team, repository  
        * meta.version, description, maintainer  
        * db\_uid (preserving SQLite asset relationship bindings)  
     4. Update only dynamic asset inventories, file hashes, and schema definitions.  
> 2. **Explicit Reset Protection:**  
   * Regenerating db\_uid or resetting version to 0.1.0 is prohibited unless the operator explicitly passes the \--force-new-identity switch.  
   * Without this flag, pyprojectmgr init and re-baseline operations must behave idempotently with respect to project identity.

## **4\. Item 2: therm Promotion Contract (promote())**

### **4.1 Formal Ruling (R-THM-01)**

The promotion contract specified in THERM-SPEC-001 Rev B §4.4 is **RATIFIED** with the following formal invariants:

Python  
def promote(self, total: float, \*, current: float \= 0.0) \-\> None:  
    """Transition thermometer from indeterminate to determinate mode.  
      
    Invariants:  
    1\. One-way transition: raises ValueError if self.total is already set.  
    2\. Positive total: raises ValueError if total \<= 0\.  
    3\. Work clamping: clamps current to total if current \> total.  
    4\. Snapshot preservation: stores pre-promotion work in self.promoted\_from.  
    """

### **4.2 Invariant Verification Table**

| Condition | Expected Behavior | Rationale |
| :---- | :---- | :---- |
| self.total is not None | Raise ValueError("Cannot promote an already determinate thermometer; use set\_total() to adjust bounds") | Promotion is strictly a one-way mode transition from indeterminate to determinate. |
| total \<= 0 | Raise ValueError("Total must be strictly positive") | Consistent with \_\_init\_\_ constructor contract. |
| current \> total | Clamp self.current \= total | Consistent with update() boundary clamping. |
| total \== 0 discovered | Caller must **not** call promote(0). Complete indeterminate phase and invoke finish(). | Prevents division-by-zero hazards and preserves semantic honesty. |
| current omitted | Defaults to 0.0 | Standard for two-phase operations (discovery $\\to$ processing). |
| current provided | Set to min(current, total) | Accommodates continuous streaming workflows (e.g. Content-Length header arrival). |

## **5\. Item 3: therm Elapsed Time Ownership & Monotonic Clock Injection**

### **5.1 Formal Ruling (R-THM-02)therm Elapsed Time Ownership & Monotonic Clock Injection**

### **5.1 Formal Ruling (R-THM-02)**

Elapsed time calculation and throughput rate telemetry belong strictly to ThermometerCore.

### **5.2 Architectural Mechanics & Invariants**

> 1. **Domain vs Presentation Boundary:** Rate ($\\text{items}/\\text{second}$) and elapsed duration are analytical domain properties, not formatting details. Centralizing them in the core ensures consistent telemetry across CLI, logs, GUI, and API consumers.  
> 2. **Clock Lifecycle:**  
   * The clock begins upon model instantiation (\_\_init\_\_).  
   * Calling reset() resets work (current \= 0.0) and restarts the clock.  
   * No separate start() method is added to the model, preventing breaking changes to the existing API.  
> 3. **Monotonic Clock Injection:**  
   * Constructor signature: def \_\_init\_\_(self, ..., clock: Callable\[\[\], float\] \= time.monotonic) \-\> None.  
   * Injected clock enables 100% deterministic, sleep-free unit testing for Gate B and Gate C using synthetic mock clocks.

## **6\. Item 4: Delivery Standard — Dual Version/Build Tracking**

### **6.1 Formal Ruling (R-DEL-01)**

Stager parameterization to support dual version tracking is **APPROVED**.

### **6.2 Architectural Mechanics**

> 1. **Decoupling SemVer & Build Counter:**  
   * VERSION.txt: Contains the package SemVer (e.g., 0.2.0), auto-generated from \_\_version\_\_ in src/thermometer/\_\_init\_\_.py. Never hand-edited.  
   * BUILD.txt: Contains the monotonic release build integer (e.g., 104).  
> 2. **Stager Authorization:**  
   * The ratified delivery stager (PREP\_AND\_STAGE\_THERM.bat, PREP\_AND\_STAGE\_BFT.bat, PREP\_AND\_STAGE\_EDSM.bat) is authorized to ingest both VERSION.txt and BUILD.txt.  
   * Gate E release-contract tests must assert 100% alignment between \_\_version\_\_, VERSION.txt, BUILD.txt, distribution wheel metadata, and built\_build\<N\>.md.

## **7\. Item 5: Strategy & Sequencing for pyprojectmgr Vendored therm Retirement**

### **7.1 Formal Ruling (R-PPM-02)**

Retirement of src/thermometer/ from pyprojectmgr will execute as a **dedicated, zero-behavior-change maintenance build sequenced after therm 0.1.0 packaging and prior to therm 0.2.0 rollout**.

### **7.2 Release Sequence & Blast Radius Isolation**

\[Phase 1: therm 0.1.0 Wheel Packaging\]   
                   │  
                   ▼  
\[Phase 1.5: pyprojectmgr Maintenance Build\]  
  \- Remove src/thermometer/ & debris (thermometer.zip, thermometer\_\_init\_\_.py)  
  \- Ingest therm-0.1.0-py3-none-any.whl  
  \- Run full pyprojectmgr QC regression suite  
                   │  
                   ▼  
\[Phase 3: therm 0.2.0 Development (promote, AutoRefresh)\]  
                   │  
                   ▼  
\[Phase 4: therm 0.2.0 Consumer Adoption in BFT & pyprojectmgr\]

* **Rationale:** Retiring the diverged vendored copy (19 lines of header drift) against verified 0.1.0 guarantees zero behavioral change and isolates packaging hygiene from 0.2.0 feature additions.

## **8\. Item 6: Integrity Guard Path Regex Gap & Batch Stager Hardening**

### **8.1 6A · Path Rule Widening in bundle\_integrity.py (R-BFT-02)**

* **Defect:** \_BUNDLE\_ARTIFACT\_RE currently requires \_bundle\_ (trailing underscore) or src\_bundle, failing to match singular bundles like therm\_bundle.txt and self-build artifacts like bft\_self\_build103.txt.  
* **Ruling:** Widening approved. Update \_BUNDLE\_ARTIFACT\_RE to:

Python  
\_BUNDLE\_ARTIFACT\_RE \= re.compile(  
    r'(?:\_bundle\[.\_\]|src\_bundle|bft\_self\_build|\[a-zA-Z0-9\_\]+\_bundle)\\.(?:txt|json)$|\\.zip$|\\.tar(?:\\.\[A-Za-z0-9\]+)?$',  
    re.IGNORECASE  
)

* Preserves primary path exclusion for singular bundles and self-build manifests while maintaining strict nested content marker validation as secondary defense.

### **8.2 6B · PREP\_AND\_STAGE\_BFT.bat Argument Hoisting Fix (R-DEL-02)**

* **Defect:** Invoking shift prior to evaluating %\~dp0 causes %0 to point to CLI switches (e.g. /dryrun), resolving ROOT to C:\\ and aborting.  
* **Ruling:** Approved. Apply the root hoisting and fail-closed switch parsing pattern previously ratified under R-01/R-02:

Code snippet  
:: \--- Hoist root resolution before shift \---  
set "ROOT=%\~dp0"  
if "%ROOT:\~-1%"=="\\" set "ROOT=%ROOT:\~0,-1%"

:parseargs  
if "%\~1"=="" goto :endparse  
if /i "%\~1"=="/dryrun" ( set "DRYRUN=1" & shift & goto :parseargs )  
if /i "%\~1"=="/y"      ( set "ASSUMEYES=1" & shift & goto :parseargs )  
if /i "%\~1"=="/norun"  ( set "NORUN=1" & shift & goto :parseargs )

echo \[ERROR\] Unrecognized option: "%\~1"  
echo Usage: %\~nx0 \[/dryrun\] \[/y\] \[/norun\]  
exit /b 1

:endparse

## **9\. Action Matrix & Implementation Authorization**

| Item | Focus | Lead | Target Milestone / Build | Immediate Next Steps |
| :---- | :---- | :---- | :---- | :---- |
| **1A** | BFT Config Separation | John | BFT Build 104 | Implement UserStateStore under %LOCALAPPDATA%, make bundle\_config.json read-only, update UI callers and tests. |
| **1B** | pyprojectmgr Manifest Identity | John | pyprojectmgr Build | Implement identity carry-forward in create\_baseline\_manifest(), add \--force-new-identity flag. |
| **2** | therm Promotion Contract | John / Paul | therm 0.2.0 Phase 3 | Implement promote() with one-way guard, clamping, and promoted\_from tracking. |
| **3** | therm Elapsed Time & Clock | John / Paul | therm 0.2.0 Phase 3 | Move elapsed calculation to core, wire clock: Callable\[\[\], float\] \= time.monotonic. |
| **4** | Delivery Stager BUILD.txt | John | therm Phase 1 | Update PREP\_AND\_STAGE\_THERM.bat to read BUILD.txt alongside VERSION.txt. |
| **5** | pyprojectmgr therm Retirement | John | pyprojectmgr Maint | Package therm 0.1.0 wheel, purge src/thermometer/ and debris, verify drop-in parity. |
| **6A** | BFT Path Rule Widening | John | BFT Build 104 | Update \_BUNDLE\_ARTIFACT\_RE in bundle\_integrity.py. |
| **6B** | BFT Stager Option Hoisting | John | BFT Build 104 | Apply hoisted root resolution to PREP\_AND\_STAGE\_BFT.bat. |

**George**  
Lead Architect (pseudonym)

![Artifact icon][image1]

TEAM\_George\_Config\_Ownership\_and\_Architectural\_Rulings\_2026-08-18.md  Created Aug 18  
Open

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAABS3GwHAAAn+ElEQVR4Xu2dWZQkR3WGyz7HL4YHDvbxo1/85uODWgwIITCrjdmxMCDMjBACJCxAWIABYzAMoO7q6Z5933s2zUgIxCojLBBiszDGmMXYgNiFMWYxoI3d4fgj7s26eSMyK6u6KjJrOuqc/2TmrZ6RJuL/4t5YqrrXy6/8yq/8yq/8yq/8yq/8yq/8yq/8yq/8yq/8yq/8yq/8yq/86tjrAfPmj+b65rXnLpjT5/bNbfZ667nz5l+tvm9lZlUvusEct+plpVEQ6LLmNpr7WZO80uo/reENNDc/RPiZGdKrbzbm8hvMIate1vQVBLoqO9pvlaYuRk3cy2eSNtasCABAl73DHLbqZU1XQaBrssZ/8Dl2xIfx2ejOLAwCxQoQ+L0ZFQPgILjBHLHqZU1PQaBLsgbfBlM4U5Ox2ezFM5teQFHcz6AkABmC6SsIdEG9jeY3z1kwZ2QpwyavgqGyHOKfnxFpAKAX3mCOWfWyJq8g0AXNYWWHDMEQRK9scI6xZtD4LG1+1gvebk5Y9bImqyDQtqwJ5tnUwWhPppfvFSBQrPRn6HmWpI1fguBtFoK32XbKmpiCQJuau9o8DSZwxiYV9bGMy5Ffg0Lv8/OsSZte69K3mdNWvazJKAi0pfMWzO9YA9zJo3phcAFDIPyc+BkJiCwrZkna8DHZ9rpWt1/WeAoCbcmO/seKkZzF5mYgcC/iUiUA1D2DMgvSZq/SpRmCiSgItKEHLJvfs4b9dWFamEEanJ/7dKVnLQlC6WciRuuqtNHr9Ly3mrdb9bLGVxBoQ9asb0Tny5Gdn9nA7p7eLwwv3g/MLmGYIWmTD9PzMgSrUhBoQ7bjv6ANr83Opi7F5Hv6ffrzsyZt8Ca65Drzbqte1ugKAqm1btH8vut8YeDimWMEB78nze6eZUyM/rMobe6muiRDMJaCQGrZun59yeDK+IU51Agv34vdF2DQvGFWpI09imx7vle3b1a9gkBq2U7fgo5nCGQpJGFwz7gKQ0dHewWQLjG6Lm3qUbXhWvN+q15WMwWB1LImfac0eGF6AgGxEgQAQD4rQNzPi+taygCsi681N1n1soYrCKSWNeon9CS2yAT0rN9nsxT38r3Iz82StJnH1YYz5gNWvax6BYHUska9vRjxF8qjfsngkB3NgwzA7+PK74n312IGYNkB5mY94GSVFQRSyxr4e67zYXg1kpdKIAYkAkDtaL+GAYDsIPMhPehkDRQEUsua9x42cDDpVQC4GAHAxg8yQMRUsyRt4EloQy6HKhUEUqswMpsdYsNHYODjEBwrGUgCgPsZBEKbd1LacNrcatXLKisIpFYJAAkBx3CvYHgg3sN8gKHQINDf6e7xc/zfmAFp405SdsD5oB6A1rqCQGoVnS8AgNjEcsQvjB0xfKVmLAto005aG3ImKCkIpFYtACoDyPd4ZC8Mrksefp4xacNOQ+tPmw9b9bIsADqQWmMDoO61JCj6vS5Lm3Vauvi0ucWqt9YVBFIrA1CWNuo0tT5ngpwBuiZt0mlr/RqHIAikVgagLG3QFNqwhjfLgkBqZQDK0uZMpfVrNBMEgdTKAJSljZlS69cgBEEgtTIAZWlTptb6NQZBEEitDEBZ2pBtaP0agiAIpFYGoCxtxra0fo1AEARSKwNQljZim1q/BiAIAqmVAShLm7BtbTjLzw4FgdTKAJSlDdgFbTiLIQgCqZUBKEubryvacJZCEARSKwNQljZel2T768O6/2ZdQSC1MgBlXfne0Hhd0oaz7NhEEEitDEBZl90Qmq5ruviMudWqdzYoCKRWBqCsZ54IDddFbThLPmgfBFIrA1DWo3eGZuuqLj4LvncoCKRWBiDUS98Tmq2runjGIQgCqZUBCPXEA6HRuqyLrzPvs+rNooJAamUA4nrRO0OjdVnPvdb8g1Vv1hQEUisDENd5m7q/JKp1yQz+ko4gkFoZgGo9dIsxV7wrNFqX9by3mnfrX4HVZQWB1MoA1GvdoisvAqN1WbZf36H7uasKAqmVAWimR+8y5iXvDs3WVV36VnO9Va/rCgKplQEYTY/aacyzThpz+TvsHOHG0Hhd0qXXWwiut/3cYQWB1MoAdFjUdk3aGaXaBVuNecxuYy5ccWWQg+AFbzPXWvW6qiCQWhmADmsEAPhe9td5S/5ox6XXmaNWvS4qCKRWBqDDWiUA3K/nLxvz5KPmZVa9rikIpFYGoMOaEAD83jlXm4usel1SEEitDECHNWEAoAe8xTzeqtcVBYHUygB0WFMAAM/nvNmca9XrgoJAamUAOqwpAWB19wOWzX2sem0rCKRWBqDDmh4A+NVX2616bSsIJJduGNGoGYCWNU0A7P26zeZ3rXptKgikVqxhuFEzAC1rygDY+Ausem0qCKRWrGG4UTMALWvKAFi9a857oDUFgRYUaxjfaBmAdjV9AL4xF/ohqYJAC4o1jG+0DEC7mj4AP5kL/ZBUQaAFxRrGN1oGoF1NH4B750I/JFUQaEGxhvGNlgFoV9MH4OdzoR+SKgi0oFjD+EbLALSr6QMAaT8kVRBoQdGGcY2WAWhX0wfg13OhH5IqCLSgWMP4RssAtKsMQBLFGsY3WgQA3QFVKn42AzC+pg/Ar+ZCPyRVEGhBsYbxjSYAeCA1JPRAkryXKnVSBmB8ZQCSKNYwvlHZ9CMCUHqvH4Eiq5mmD8AvlReSKwi0oFjD+EalxoP5SwCQqYMr31PHBe/x35vVTBmAJBo0VB0AFGNTrxPXdXyl+wAIvlfSnZmlNH0AfqG8kFxBoAUFAKDBnEEZAKXC8LhKiVgTADIIQ5QBSKJyw1FjsjEL04urNP2DIoqCIf6uOukOXtOaPgB5J3hONxw1pjRlUd5AEcPHVJh/McMwtjIASdQIgAfhKgz+YHGNqYBhMQIFRH9vhqFGfX91fVMh+V6pH5sB8LOIH5IqCLSgQSNGAGCTAoDC/ItkdHs9z17P4yvdF++Ln63MEBD9N7Tpq6RNcNaq769F/0Qk3yv6MgPQXKVGZAD6ofkfjCuZujC8vT5Equ+vARD054LsQBoXBm2Gs059fy36JyL5Hu7dc0MAzlkwP7XqtakgkFqlRqTGKpY3IZh0YWBemFqa/XySvpdwFDDQ31EFQgkG/u/j/6eBtDHOCvX9NQMwRZUaNAJAMeqTtPEfCm1S9/TstKmcJZrCkLOCmToAc/kDMWUAeMPLAQAjLkQAIFOz2S+w1wv4SveIu/cFHJwZRgVhTcPQ99c5HReS7+HePTcH4B7th9QKAqklG1MC4My3IMoeiIwsjf8wqUV/dUAIFTDQnx8XhhgIZzUMfX+d03Eh+R7u3XMGoLlkYzIAbvSHFgYAnA+RiZ3xyewPh5boyvdLAgq65yyRYRhBfX+d03Eh+R7u3XNzAO7WfkitIJBasjHZIAyAHP3ZrDBxYXyrP4aW6Mr3GgiGgUFQMBTzBQkD/bfHhUGbvkraUJ1S31/ndFxIvod795wBaC7ZmHUAsFmd+dnw9voIoUfa2CNVTMLBUGgYJpUVVgODNlYn1PfXOR0Xku/h3j03B+Au7YfUCgKpJRtTAsAmc6N/n0ofAsAZfxOZ3upRy3Sle352WhYwVIAwjRKpBAP+TSRt/Ji0yVpT31/ndFxIvod795wBaC7ZmM78C2r0JzPK0oeNz6Z/9DJJ3DsYGAjx88Ng6FKJpM2WXH1/ndNxIfke7t1zcwDu1H5IrSCQWtx43OkaAJ748qQXppWj/WOEHkuSsQIM/jMTgmHVWQGif682fkzaeEnU99c5HReS7+HePTcHIH8zHDcem58B4Nq/mPguDkZ/GB+GLky/2V//BNrsxTDgPQ1EFQgoq2phECCsFoYSCBD927XxY9ImnJr6/jqn40LyPdy75wxAc3HjVQHA5Q+v+HDN/5ilgen/dDNJ3DMITgyDAmGcrBCDIVoijQuDaAdt/Ji0ISeqvr/O6biQfA/37rk5AD/WfkitIJBa3HgFAGQSCQBGf5gRIzTX/M78ZPbHCf0ZrlvKsQIKAmZSMNSVSKnnC1OBoe+vczouJN/DvXtuDsCPtB9SKwikFjceAwATwBhy9acAAOZf8qblkd+Zfos3/uOhLV54dqL7cWDQIDSBYdwSaZIwaJOOrb6/zum4kHwP9+45A9Bc3HglAMgsXP+72n+TNyPMiboe5Q6P+Gz6J9j7J+BKz4UIDoaiBEMDEGIwVIEQK5FGhaEJCElgmD4A/6v9kFpBILW48YYBgE0uGNGN/mRgjO5s+CeSnrTVXiGObVVQVIGwuVlWGAWGpiVS6fMLY8CgTR+TNm4jTR+AH2g/pFYQSC1uvBgArvwhcxWj/7I3K4/8bPon2euToa1eLsYSgHQRhnGyQgkGaruJwzB9AH6o/ZBaQSC1uPEkABgRYQwGgCe/WPmBKWFUmBdGdsYn0z+FtU3c03sOCvr5icFQA8LQJdVNM1AiTR+AnAHQONwZfP6fAZD1P09+UbO70mezL2/Y+E8lPc2a/6kQx+h+HBgagzAEhioQYvOFWInUGgzTBmDefN+q16aCQGppANCpGgDU/1z+uNGfTIvyxpnfmvxp9vrn0DYvgFAIYAhIJAxNQEgBQ12JVIJBgDAODNr0VUoCwIL53lxkUEypIJBaVQDAADAD1/+y/OHSh0d+Nv2F0HaSeC5BUQHCtGFgEEaBYVIl0tgwTB+A/9F+SK0gkFoMgKv/F3wHFhNgAgAGeuwSlT+bqfTZMjA/m/3pVn+x3evpUuJnpglDExBGyQqxEikKgwBhGAwxECph6PurNn0GYIIaBgBPgHn1B+bj0gcmdsYn0z/D3j8DV6UCCoJkNTA0AWEaMDQtkapAaApDFQAyriFYBQDf1X5IrSCQWlUA6AmwLH9gSh79edSH0Z8J7SDJ51FgAFhVIBAMo2SF1DBMtESSANB9HQhzpKYAnLNg/lt/S0hqBYHUGgYA1/9F+bOFRv+t3rgwM5v9WVYX7fB6lhS9xz9XgqEKhBGywqgwrBaEAAYBwmphKIEAUf/EAJDZQULQFACr7+gBMbWCQGppANBBDgDqaAmAK3+2+FUfN/qTkWFymP7Z9v7ZuO6kq7gvwKgCwWrHTcbcdrsxP7zbnHWv791lzC1fMmbje0aHgb+mxt1Tf8XKoyIbNAfg29oPqRUEUosbDwDg6w/RKW4JlEY9ngA/TgEgR39nfqu/hHYK8TPDIEEQMFxxxJjPfENb5ux9feJrNrvtbTB5XoxkBeqrEgwkBsD9Np8MQDNVAYD0XgBA5Q/X/yhPULZg9Jbmf47V+p1ez6Er30MOiAgMX/wvbZGz//WZOxqUSAKAIiuQ+YvySICgAXDGrwfgDu2H1AoCqdUEANTNsv5H+YPaHRNcGJkNvgHaRZLPNTDsu1lbY+28rr5xyHxhMV4ayRKJv8ayVBLNEwR4rgHAxr9lhTK4NQWB1KoDQK4AFeUPJr+i9oeJYWyY/GLIGv65u/y1EL3HUEgYPruGSh/9QilUO3EmGDgbxOYKRVlEABRqAIDVN/WAmFpBILViAOCrD+USKCbAOPsDALAyg8kvance/THKO+Pb+0vs9ZLddBX3gMKBoUD48T3aFmvnhcl+kyVVB4IGogKEUQA4Z9582arXpoJAamkA3McgeQVok18mZACw+4vzPpj8YgKLCS5MzKP+86DdJPlM9yUQCIa1DkDdrjN/y3bT8ogB4KsDQNzD9G5yzAAsmM/pZfHUCgKpxQDwL8FAIxcAYAl02a8Acf2P1R+e/GL0h4nZ/JdaPX+316V05XtIgsAwfO6b2hZr5/XPXxuy0bZJZASGoR8pjyKZQEIgYZAAWH1WVwSpFQRSqwQANS4A4ENwvAJU1P9i8ovR35lfGP4Fe0i45+caGHbcqG2xdl6vu6F6s03C4DKChEFmBAZhcQAA+rJUDmkAvPmhf9N+SK0gkFqcMvUmmF4CZQCw/MmTX9T+GMkL81u9cE9EiDMQGgb75z/9VW2Ns//1sdsrdp0lDEvxjBCA0FclUQaguQoA0IgRAHgFCPU/JsBY/nTlzw5fx2MUZ/NfZnX5HqW9/noZScLAILzimDG/+JW2yNn7uvfndhDZ1+AIxtIgGxRfOY/+AQQiIzAARUlEA5qEoAKAT2s/pFYQSC0NABqUAZBLoG4CTPU/jjdw+YNRHGUOzA2jv2gvCff8TPclEAgGmRUO3WzMp75izI/u1paZ/dcP7jLmo182ZvHG0c8jFV85L4DgCbPMBKU5AfoVJVEEAJ4Q2zngp/ScMLWCQGpVAYCGl0ugT9lC9T+t/mAZE+UPjFuY3+qvrOGv2Du48j0kQRgGQ2y+ICfPvKTKy6pVG21611kewYidR4qdUuVPtk3jYF4tDMvljMBzBTlPCDIBiX+rZzEh7ocA2OunrIK9oZQKAqnVFACeAMM8vPqDyS+My+a/wurF1ugv3kdXcd8YBvo7YzBUgkAwxDbaxoUh5Qd56k6pFtmAYaDszOVRsXS6qQwBzweGAPAv2g+pFQRSKwaA2wVe8qdA0UnoSJ4AX7S9XP7AtChzYGoY/SX7IkKcgdAwEAgahklkhWEwNAGhKiuMC0MTEAoYNouMABgICJ0N3LyAMkExKWYI0L99D4ArhXiDzOuT2g+pFQRSqwoAPgbNAMgJMK/+wJgwbGF+q5daw1+5b3C9cv/gGaqDIQbCqmCIZIYCBIJhlKzQFIYmIDSCYXM5IzgYlgZZQU+Ui9WhGgCKHWKfBT6h54SpFQRSaxgAvASKHWA3Ad4xWP2BMV3pQ6aG0V+2n4R7fqZ7BwSDQDDEQKiFYXcNDCOAUJUVRoWhDoTVwlAqjxiGpUE2KCBAJliiUogAQBbQG2QZgIgkAMW3QRMAvAfARyDQ+TCKK392eUPCrDAzTA2T//X+ga4i8XMMhEnDME5WaApDHQiTgsGBsIVA2FKfEYpMQHMCzgKuFJJZoAIAWw7dZtVrU0EgtRgAtwtMACCl8iYYL4HyChDW/3n1B2aEUQvz7/OGf/kBK1zFfQkG+vkoDACqCoYqEAiGaFZYJQwxEIZlhZFhiIDAMBSlEcOAbEByEIhM4CbFIgtEAWDze/2TLolTKwiklgOAGqoAYKm8CYYlULcDvN0bhFd/MPnl0gfGhtFfcSAixBmIMWFYTVYYBkMTECYFQy0IOitsVVkBECyXs4FcKUIp5PYIaC4gs0AUgHnzcT0gplYQSK1RAMAKEAwCALDrCyO60Z8MDZO/8sBAfwMd9FeO1cFQCQLBEM0KY8IQA2HSMNSBMBQGgLC1OiPw3IAnxu63cYpVIV4R0kuiKgN8TA+IqRUEUmsYAGh4dE6xArTTG4jLHxjVlT0w/35v9ldZ078KV3XvgFAwxECohUFkhQAGAkHDMM0SaZpLqpwVOBs4GDA3oJIIEPBSKUohLoP4uASyQB0Ac/Pmo1bB12WmVBBIrRgAmFAVm2AEAL70yq0A7fTmgcmwyQWTOvOTyV99cKDXkPi5DoRKGOi/0RSGoVlhgjDEQJgIDAzCNlUeiYyAbIBMIEshLoN4LiDLIAlAAcG8+bCuCFIrCKSWBgAN5wBArbk82AOQK0A4+4PRFqUJTIo6H4Z+9QFv+L89ZIWruC/BQCCsFoZVl0gjwFAHwqphqAJhW1ga8fzAQUDlEJdCbpMMK0KyDFIAlLJABqAMAFYOqgCQK0AwDo49wHwwJ4/+rzngDf9arYNeDMVqYBhaItXBQCBEYdg9gKEOhInAUAWCzgrbBQgkzMccBFs9BCiH3MrQZpoL8GQ4BoDIAlQG3apL4tQKAqlVBQBGFKw48CYYnwGCEWAYmAuTXxgUdb4b+a3+7tBAr4MO+yvHmsAQgEAwRLNCHQx7h8MQgEAwNMkKTWGoBKEOBoCwPZ4RZDkkSyH0Ge8LFGUQAcArQQqAD2k/pFYQSK0YAO4cEADY7AG4kABAh2IDDIaBsWA+GBTmdeY/6M3+emv61+Oq7h0QCoY6EKIwEHRRGAiEKhiiIOytyQpjwFAHwqgwcFYoZYOtg7IIfVNkAZoLuCVRPQ+wKj4xVgbgg9oPqRUEUguNgYYpANg0AIB3gdEBvATqJsDWNC/d640Hc8K4MDPM/feHy3qDuK8DYdIwVIIwQRjqQFgVDNsJhh0DEPir5jEYOQi2DVaI5FzAlUF6HpABqBYfg2AA+CSoPAaBmhTf+8krQDAKTAXTwZio+2FkmBuGf8MRf30jdMRfXZxhoJ+dFAzTLJEYhjoQVg1DFQg7wtIIfcHlkMsCPBfYUp4M86bYEAA+oP2QWkEgtUoH4SIAoJEdADt8B6LTYRIYCsaDMTHRdeY/5A2/UeuwlwOiBobrP2TMv3/dmJ/coz9P1f4Ln1LDZ5eP3DwBGHYOYKjNCjsFCJwNMDdgCGg+wHMBlEG8McbzAD4hio9MRgC4WfshtYJAatUB4HaBt/pG5yVQdDjW/1FvY/TFKM2lD8z9piMDvRk66q8ci8Gw5Ywxt9+hLdfd1xe+Zf/dx5tnhkoQhmWFnfGMwCURIJBzAZRBbk8gMg9gAHA8mvcCrN5vhTK4NQWB1IoBgJUEPgbBm2C8BIrORh3N9T/KFUx0YWQYG2Z/izX9W3BV9w6ICAzf/K62WPdft3+nZr5QAcKoMLiMQBAU2UCUQ5iboRRCmYosgIztyiCxHCoBcDvCGYCyJAAPVQDwRyEZAHQcOhr1s6v/D/q6HaO/M/9hb/irSfNCLhYB4V0f0daandeJW0afODeCYSfBsEuBAAi2D+YFXArxXAADltsTWBLzgEVfBsUAsBXATboiSK0gkFpNAECDrycA0NEAAJNO1P8ofzD6w8wwtzT9ArTirzEQoK98W9tqdl4ohVazilTAQCAwDDIr6NKISyLMCTgL8N4A+ksuh1YBUMwD5i0Akc3RlAoCqaUBQN0oAeBdYHQEOgqdi4854uAbVmcwecVEFyM6jA2z91eUEGMgFAx331s21Sy97ry3ZhWpDobdAxhqs8JuDwJ/5byDAOUQzQdcFtg+mAzzPICXQzERLi2FagAWzPv0gJhaQSC1YgDgZKE8BoG6k/cAsDyIHWDU/1j+RPnDoz+bf5G0CTrmrxzTMMw6AI32F6pAGJYVdg8ygssGgACTY4aA5gKuDNo2mAeg7xwAS4OVoCgAOQMoABYFAJt9g6Jx0dByCRRr61iLR/2PlRyM/hjRYWw2/dIKSdy791bKMHx1hkug//jW8P2FxlkhAoPLCARBkQ2oHMKcAKUQsoArg7b51SCeB/BEmFeCKgDIh+GaAICJFwOATsUKEDalUP9j8ouJL0bzxaPe8MtCm+XzSgjC2z9Y8tRMvY7cNGSjrS4r1MGwm2DYE4KA38EACHg+gLkAJsO8GuR2hTUAmwYfjpEAzOUPxVcDUJwDIgDQ8OgUdCg+5+vqfyp/ePSHudn00BboOF0lDCvlrPDlGfyK9M9/fcRd5zoYCAQNA7KCLI0YApRDLgvQXKAog2gegDJIToQBQPHhmPIc4LO6JE6tIJBaMQBwFFoCgJHmEtvg+BgkzgBhBxgbYKj/Uf640X/FGxtG32pNv5WvfM9ACEAYhn3XGfPLX5UN1uXXz35h/92nJnsEI5oV9noQXFlE2QATZJ4TIAsUZdB2vxok9wPkkYgYAPb6pXXeA60pCLSgAgB3FFoAwOeAMNJg5OE9AOwAYwMMy5+Y/GLii9F884o3/DbSduiEv3KsDoYbP2LMl75hzF33KMd14IXjGZ//mjFnbgnPIg07mKdPqTbOCntVNgAEmBwTBMgC2BvAKh1WgwAAzwNKK0EVAFh9Xe8LpVYQSC0GoPg0GAEgD8IBAN4EQwei43H0GRNgLGXy6A9jO+OT6XdAJ+jKQAyBIVYi6Ylz1ZKq3F+o2nWOnUfis0iTOJhXBcPQrBCBgTOCLIuQDTAncKUQzQV4NQgrdu5YhFwJYgA2ZQCiGgYAzgFh7Zn3ANB52AF2E2Aqf9zoD/Mf84bfKbRLPjMUCoYYCJOGoQCBYIiBMCkYJvZBnn0CBMoGmIfxfICzAJdBmAcUG2I0ES4OxUUAsCXw13RJnFpBILXQGKXPAwsA8PE7jCwMANIy0jk6HSaBoWBAGBUGhqHZ9NBu6CRdJQwVIEwKhjoQmmaFpke2SyAcrMkKdTAQCBoGZIVSNgAEmA8QBMgCWBFChsZqEOZrmAg/kVeClgeH4gCA+7rEcga4XQ+IqRUEUss2xv9pAPjDMAAAIws2X1B7oiPQaehwGARmgvnc6A/zHyfjW9Pvsdc9uPI9AyEAmSQMMRAmBUMlCARDk6wwrERiGEog7PcguLKIsgGysCuF9viy1E2GaTUI5SrPA/hkKC+FOgAWFQB982WrXpsKAqllG+PXMQD4KDQDwJtg6DDsALsJ8FFvPpgTxt113Bt+L2kfdMpfOTYJGOpAmDQMrZVIAGF/mA2QhV0ptMfPBVwZtMOXQShXGQBeCo0BUByImzdftOq1qSCQWroEQs3IALiToNt9muVNMHQURj6YA2aC8bDyA9PC0IXxrfZDp+gq4nUwjALCRGCoA4FgiGWFpiWShqEyK0Rg4IygIeAsIMsgLFWjr9y5oIq9ALkZ5gBYMJ/TFUFqBYHUsgDcWwJgiQDYMjgJigbmTTB0EjoZxoCRYDpX/pCZnfGt6Q+QDor7AyOAMG0YAhCGwSCywjAYGpVIdTDsJxgOCBAoG6APXCm01/cJJsNYDcLRiGIiLJZChwDwae2H1AoCqWUB+JEGwH0aTACABmYA0EHo3Dcd9uv/MByP/vtODEwPHYKu8VeOSRCmDUMTEFYLwzRKJIYBWaGUDfb7jUhXCu31WcCVQbQcir5yE2FaCuW9gACAPs0D5s1tuiJIrSCQWrYhvusAWPRHZx0Am/2WOp8EBQBuF3if7xx0LE+AYTYe/WFoZ3wy/WHoGroyEFOGIQbCpGAIQCAYmmSFpjCUQDjoQXBl0YFBSYRSCFkAcwEug7Acir7izweU9gKWyschxGeDP6AHxNQKAqllG+IrwwDACIPlN94EwxkgBgBmgylhWJjZGR+mtzpidZSurLFgIBAYhiYgTAqGEghHm2WFcWEIssLBMBtgcuxWhvb5uQCvBuGoNCbCvBKEIxE40FgLwLy5QQ+IqRUEUss2xKdHAQCjEzoVJoBpYDRX/mD0P1k2PrRy2ko8axA0DLUgnBwvK9TCUAcCwVCXFUaFoRIEgkFmBc4IEoKr9g2yAMogtxpEy6GYCGMlCP0GALAU6jbDlsrHIRgAq8Pr/CDYmoJAC3q/+06gCAD4SkSMKg4A2gXGyISOhAFw9Bkmw9InzAoTO/OT6Y9Bp+kKGEhVMIyUFcaFoQqEYTCIrNAUhlWXSIc8CO4r5g8OyiGUQhiMMBfgMgjLodgQcxNhsRfAx6JjAJy7YPp6YzS1gkBq2YY4LAFAY2kAUGPyMQgAgE6cP+JNA4MBAJgVJuZRH4Y/froshoFBSAJDFQh1WWEMGKZRIiErlLIBIKBJMSbEWJTAahCWqAEANsQkAHIvIAaALYEv0yVxagWBFnSVBgBftOo+DBMBAJ3h9gCOeLPAYDAgTHrkFJmfDH8COkPXITAEINTBAOAUDENBmAIMfYJhlKzQFAYHwmEPgoPgkIcA5RBnAcwFXBmEifDu8kqQ3AtgAPjbokUJ9JBIRZBUQaAFPaQSgG0DAPgckAPgiO9wBsDV/wSANP9J6AxdSVEYrhkCQxUIBMPIWWEMGOpAqMoKo8IQgHC4nA1cOUTzAWQBlEFYDcIKHfYDeCUIE2EshWIvgDfDis8GDwD4acQLyRUEUqtnzG9YAL7TCID9ZQBgDhiK6/+jp8j8NOqfOlOWhIFBkDC0Ml8QIDAMdSBMCoY6EBgGnjSXIKBJMSbEyMg8D8B+ADYseSWIAeDNMAkABjzb9/+ovdCGgkAbsg3y2hgA/GkwLLMxAEjHmNyhg/FxRwcAmRKGhZHZ6DD9NUIlGAiEyqxAMEx8vlAFwhhZoSkMdSDUwnDEg+AyweFBOcRZAP2B1SCUp5gIY79GngnCPK4AYKkMwAM7UP9DQaAN/eFGc18LwJ2jAoAzQDCRA4BM6kofmPz0wPinSePA0EpWWAUMdSCMCgPaWWYDQIDVIWRhngu4eQDtB2C1zp0JGg7Ad9YdML9l1WtbQaAtnb/JvLEOAPxKJNSdMQBgNBgRJkX5w8Z2xr92AEAMhBIMERC6DAN/3jkGwrCsMAwGCUIJgoOUBQ7680I8D8B+AEpVXgrlvQDeDcZv/SkAWDRXWPW6oCDQltZtNL9tAfjxMAAwAtUB4EZ/MjYDcObMQHUwDMsKMRimVSIxDE1AGJYVmsIQgHC0nA1cOYS5AGWBV2IesN/PA3AuCABgKRQrQTEA3PcD9c0dvY3mN616nVAQaFEP75sLmwCADsF3AFUBcM213tBnYH6tChBGhWGkVaQ6GKpAGDMrjApDDASGgfcVJARYHeK5AMogNw+giTD6iT8jXGyGAYDlAoBfnb9gHmbV64qCQNt61CZzdVMA0NkwiFsCrQHgWiENQgyGKhCGwdC1EknDUAdCFIYVD4LLBEcH5ZDLAof8ZNjNA2hDDEciikNxAgAcbycALrPqdUlBoAt67LI5OQ4AxxsAUIAgAGgCQgHD6fJcIQZCXVYoYCAQojCcrIDhRE2JdLwGBIIgmhVWKmAABCvlbIBMgNUhzgLYGMNyKOYB2BDDSpBbCpUA4DiEB+BNVr2uKQh0QRttjfikreb6WgBWqASCWQgAlwFOe7PCwDzSa/OXMoGSmzQLOZikGASSW3Iluf0Hq+OQzApW7lCeFc4pQZwRihLJyh3jvkZlhVN+lQsKssJJ/++HShnByn0djFXwvUgk9415VpshzgpW7rtUjw0yAiCAXCagUghzAewNYHfY7Qfs9wDgSIQEgHeDLQC7rHpdVBDoki7cYXbji5d4I6xYBTrsUzQ6NDYHOAXzAgIysTa5LoFio39VFogCoDJBUBZB11Rng9o5AkOgswFDILJBVWkUlEVQLBswBJwNjg0gmF/xWaAogw4P5gHYEMNKEJ8JwqCFzTB8RYoF4A1Wva4qCHRNtjEvsAB8tQDggAcAqRmdiM6GMRiAYBl0BGmjxwwfjPw15i8BcDoEQGeAsQAgCKIAnKgoiZpCcMxnAgDgIKAsgPbHPACnRR0AtBKEM0G8F2AB+NgTlswfWPW6rCDQRV28bO5z+R6zvzgKQQCgw/gsEEwDU8F0vBSKTIBrUMZQKVMnbfio+Ulc+vARjEoAhFwpFIPgmgalEKQhODmBcigCAZdCPBfAPADtjz0BlKO8EuQAwGbYLnPvRTvM66x6s6Ag0GW9/LC5/6sPmFfa0eezWKdeXvEdiokhDIIRFCMsjAcj8gitDaylDV0lebK0asTXpi/V/zTyS+MH5j9VkQGgqgzA5o9lAFYsA7D5RRYozQXqAJAZwJdAn3z+XnPlM/eY+1r1ZkVBYFZk0/D9bYc9wqbxy23nL1lTbLSGWThyyly3csbcZsuhO3glBqtDqxX/XTHJzTBd5uCAHlZ8pLjeL5U8JweKrgKdGKwC6ZUgZ/zjXtHVoGN+JahyNWjFCwNKdDXoqPm6Nf/H33LU3PrmQ+bWNx4y173+oFmwc4Dnv2qfedhV28z9rHqzqCCQlbWWFASystaSgkBW1lpSEMjKWksKAllZa0lBICtrLSkIZGWtJQWBrKy1pP8HiV2ZfQhqSj0AAAAASUVORK5CYII=>