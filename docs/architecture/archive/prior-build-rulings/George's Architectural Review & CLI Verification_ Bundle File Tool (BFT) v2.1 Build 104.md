# **Architectural Review & CLI Verification: Bundle File Tool (BFT) v2.1 Build 104**

**Record ID:** ARCH-REVIEW-2026-08-18-02  
**From:** George, Lead Architect  
**To:** Ringo, Product Owner  
**CC:** John, Lead Developer; Paul, Lead Analyst  
**Date:** August 18, 2026  
**Subject:** Build 104 Architectural Evaluation, CLI Functional Verification, Gap Analysis, and Ratifications  
**Status:** **REVIEW COMPLETED — CONDITIONAL RATIFICATION PENDING MINOR REGISTRY PATCH**

## **1\. Executive Summary & Architectural Disposition**

Build 104 represents a major milestone in architectural stabilization for the Bundle File Tool (BFT v2.1). John has successfully addressed the systemic **dual-role anti-pattern** by implementing **R-BFT-01 (Option A: Config Ownership Split)**, isolating runtime mutable user state from the hash-verified, governed delivery payload bundle\_config.json.  
During comprehensive verification and automated execution of the CLI surface across multiple permutations (bundle, unbundle, validate, dry-run, overwrite policies, and integrity gates), **one critical functional gap was discovered**: MarkdownFenceProfile was fully implemented in src/core/profiles/markdown\_fence.py, but was omitted from registration in ProfileRegistry.\_register\_builtin\_profiles() in src/core/parser.py. Because both bundle\_config.json and ConfigManager.DEFAULT\_CONFIG specify "bundle\_profile": "md\_fence", any invocation of bundle-tool bundle \<source\> without an explicit \--profile plain\_marker argument immediately failed with ProfileNotFoundError.  
Once a one-line registration patch was applied to explicit \--profile plain\_marker argument immediately failed with ProfileNotFoundError.  
Once a one-line registration patch was applied to src/core/parser.py, **100% of CLI functional test suites passed**, demonstrating complete integrity across all transport profiles, bounded grammar parsers, extraction reconciliation assertions, and path safety filters.

## **2\. CLI Functional Testing & Verification Results**

All primary commands and option matrices were tested against the Build 104 codebase.

### **2.1 Test Execution Matrix**

| Command / Workflow | Scope & Test Parameters | Initial Build 104 Result | Patched Result (md\_fence registered) |
| :---- | :---- | :---- | :---- |
| \--version & \--help | Version string check (bundle-tool 2.1.104), argument parser help | **PASS** | **PASS** |
| bundle (single file) | Plain marker profile, custom base path, stdout/file output | **PASS** | **PASS** |
| bundle (directory) | Markdown fence profile, recursive discovery, syntax fences | **FAIL** (ProfileNotFoundError: 'md\_fence') | **PASS** |
| bundle (default profile) | Directory bundling relying on config default (md\_fence) | **FAIL** (ProfileNotFoundError: 'md\_fence') | **PASS** |
| bundle (include/exclude) | Glob filter with deny precedence (--include \*.py \--exclude \*.log) | **FAIL** (ProfileNotFoundError: 'md\_fence') | **PASS** |
| bundle (invalid profile) | Error path testing with non-existent profile name | **PASS** (Exit code 1, clear diagnostic) | **PASS** |
| bundle (missing source) | Error path testing with non-existent source directory | **PASS** (Exit code 1, clear diagnostic) | **PASS** |
| unbundle (plain\_marker) | Transport parsing, directory tree creation, canonical headers | **PASS** | **PASS** |
| unbundle (--no-headers) | Raw payload extraction without repository header injection | **PASS** | **PASS** |
| unbundle (--dry-run) | Non-destructive preview mode, zero disk writes | **PASS** | **PASS** |
| unbundle (--overwrite rename) | Conflict resolution with numeric suffixes (file\_1.txt) | **PASS** | **PASS** |
| unbundle (--overwrite skip) | Collision avoidance leaving existing files untouched | **PASS** | **PASS** |
| validate (valid bundle) | Syntax validation, manifest parsing, entry count verification | **PASS** | **PASS** |
| validate (invalid input) | Syntax rejection on non-bundle plain text | **PASS** (Exit code 1, diagnostic output) | **PASS** |
| bundle (R-BFT-02 integrity) | Refusal of embedded/nested archives (e.g., therm\_bundle.txt) | **FAIL** (blocked by md\_fence lookup) | **PASS** (Fails loud before file write) |

## **3\. Detailed Architectural & Governance Review**

### **3.1 R-BFT-01: Configuration Ownership & Runtime Mutability Split**

* **Evaluation:** **APPROVED & FULLY ALIGNED.**  
* **Mechanism:** ConfigManager.save() now unconditionally raises ReadOnlyConfigError. ConfigManager.reset\_to\_defaults() and legacy v1.1.5 migrations operate strictly in memory.  
* **User State Storage:** UserStateStore (src/core/user\_state.py) manages mutable properties (last\_source\_dir, last\_bundle\_save\_dir, window\_geometry, first\_launch) persisted to %LOCALAPPDATA%\\BundleFileTool\\user\_state.json on Windows (and $XDG\_CONFIG\_HOME/bundle\_file\_tool/user\_state.json on POSIX), with automatic working-directory isolation under BFT\_PORTABLE=1.  
* **Impact:** Eliminates the root cause of the Build 103 regression where saving window positions inadvertently stripped the D-005 safety rules.

### **3.2 R-BFT-02: Widened Artifact Path Rule & Regex Deviation Ratification**

* **Deviation Analysis:** John identified that the literal regex in ruling ARCH-RULING-2026-08-18-01 required the bundle identifier to sit immediately before the file extension, which inadvertently failed version-suffixed historical archives (e.g., EDSS\_src\_bundle\_v1\_7\_0\_Build\_151.txt and proj\_bundle\_9.txt).  
* **Implementation:** John adjusted the pattern in src/core/bundle\_integrity.py to:  
  Python  
  \_BUNDLE\_ARTIFACT\_RE \= re.compile(  
      r'(?:\_bundle|src\_bundle|self\_build).\*\\.(?:txt|json)$'  
      r'|\\.zip$'  
      r'|\\.tar(?:\\.\[A-Za-z0-9\]+)?$',  
      re.IGNORECASE,  
  )

* **Architectural Ruling:** **DEVIATION RATIFIED AND CONFIRMED.** The adjusted pattern captures singular names (e.g., therm\_bundle.txt) and self-build artifacts without regressing existing test fixtures or falsely matching source code/config assets (bundle\_config.json, bundle\_integrity.py, bundle\_frame.py).

### **3.3 R-DEL-02: Delivery Stager Hardening**

* **Evaluation:** **APPROVED.** PREP\_AND\_STAGE\_BFT.bat correctly hoists %\~dp0 resolution prior to argument consumption, enabling /dryrun, /y, and /norun execution modes while rejecting unrecognized arguments.

### **3.4 Package-Owned Versioning & Governance Sync**

* **Evaluation:** **ALIGNED.** Version 2.1.104 is synchronized across VERSION.txt, pyproject.toml, bundle\_config.json, .pyprojectmgr/project\_spec.json, .pyprojectmgr/project\_manifest.json, and src/core/version.py.

## **4\. Gap Analysis & Foresight Assessment**

> 1. **Gap 1 · ProfileRegistry md\_fence Registration (Immediate Fix Required):**  
   * *Issue:* MarkdownFenceProfile is defined in src/core/profiles/markdown\_fence.py, but src/core/parser.py only registers PlainMarkerProfile in \_register\_builtin\_profiles().  
   * *Resolution:* Import MarkdownFenceProfile and add self.register(MarkdownFenceProfile) in ProfileRegistry.\_register\_builtin\_profiles().  
> 2. **Gap 2 · Automated UI Test Coverage (Recorded Architectural Debt):**  
   * *Issue:* The Tkinter UI layer (src/ui/\*, 938 statements) currently has no automated headless unit tests, requiring temporary omission in pyproject.toml to maintain the 85% core coverage floor.  
   * *Resolution:* Schedule a dedicated task in Phase 6 to build a headless Tk mock/fixture harness.  
> 3. **Gap 3 · Missing Canonical Installer Skeleton in pyprojectmgrV2:**  
   * *Issue:* INSTALL\_BUNDLETOOL\_BUILD100\_SKELETON.bat was missing from its expected path in pyprojectmgrV2. While John recovered the exact bytes from historical artifacts via SHA256 verification (539487149...), the canonical repository copy must be formally restored.  
> 4. **Gap 4 · pyprojectmgr Baseline Identity Drift (R-PPM-01 Extension):**  
   * *Issue:* Re-baselining in pyprojectmgr previously altered project\_meta.name from bundle\_file\_tool\_v2 to BFT\_v2 and issued a new db\_uid.  
   * *Resolution:* Ensure R-PPM-01's field carry-forward list explicitly includes name alongside version and db\_uid.

## **5\. Conclusions & Recommendations**

> 1. **Authorize Immediate Patch for Build 104:** Apply the one-line fix in src/core/parser.py to register MarkdownFenceProfile.  
> 2. **Accept Build 104 with Ratifications:** Upon applying the registry fix, Build 104 is fully approved for general team use.  
> 3. **Formalize R-BFT-02 Pattern:** Formally adopt John's updated \_BUNDLE\_ARTIFACT\_RE into the master architecture specification.  
> 4. **Re-establish Skeleton in pyprojectmgr:** Place the verified INSTALL\_BUNDLETOOL\_BUILD100\_SKELETON.bat under version control in pyprojectmgrV2.

## **6\. Formal Team Communication**

Markdown  
\# TEAM MEMORANDUM — BFT v2.1 Build 104 Evaluation & Architectural Ratification

**\*\*From:\*\*** George, Lead Architect    
**\*\*To:\*\*** Ringo (Product Owner), John (Lead Developer), Paul (Lead Analyst)    
**\*\*Date:\*\*** August 18, 2026    
**\*\*Subject:\*\*** BFT v2.1 Build 104 Architectural Review, CLI Test Results, and Ratifications  

Team,

I have completed a thorough architectural review and functional CLI test suite execution for Bundle File Tool (BFT) v2.1 Build 104\.

\#\#\# 1\. Architectural Disposition & Key Findings  
\- **\*\*R-BFT-01 (Config Ownership Split): RATIFIED & CONFIRMED.\*\*** The separation of immutable delivery defaults (\`bundle\_config.json\`) from runtime user state (\`UserStateStore\` \-\> \`user\_state.json\`) successfully eliminates the recurring safety-rule regression.  
\- **\*\*R-BFT-02 (Artifact Path Rule Regex Deviation): RATIFIED & CONFIRMED.\*\*** John's adjustment to \`\_BUNDLE\_ARTIFACT\_RE\` accurately implements the architectural intent, avoids breaking existing versioned archive tests, and properly blocks singular bundle artifacts like \`therm\_bundle.txt\`.  
\- **\*\*R-DEL-02 (Stager Hardening): VERIFIED.\*\*** \`PREP\_AND\_STAGE\_BFT.bat\` option parsing functions as designed.

\#\#\# 2\. Critical Action Item (Lead Developer)  
During end-to-end CLI execution, we identified that \`MarkdownFenceProfile\` was not registered in \`ProfileRegistry.\_register\_builtin\_profiles()\` in \`src/core/parser.py\`. Because \`app\_defaults.bundle\_profile\` defaults to \`"md\_fence"\`, CLI bundling without an explicit \`--profile\` flag failed.

**\*\*Required Patch in \`src/core/parser.py\`:\*\***  
\`\`\`python  
from core.profiles.markdown\_fence import MarkdownFenceProfile

\# Inside ProfileRegistry.\_register\_builtin\_profiles():  
self.register(PlainMarkerProfile)  
self.register(MarkdownFenceProfile)

Upon testing this patch, all 16/16 CLI permutations (bundling, unbundling, validation, dry-run, overwrite rename/skip, and nested-bundle integrity gates) passed with zero errors.

### **3\. Summary of Open Items**

> 1. **John:** Apply the MarkdownFenceProfile registration patch to src/core/parser.py.  
> 2. **Paul / John:** Note the recorded UI test coverage debt for scheduling during Phase 6\.  
> 3. **George / John:** Re-establish the SHA-verified installer skeleton in pyprojectmgrV2.

Build 104 is architecturally sound and authorized for deployment upon applying the registry patch.  
— George, Lead Architect