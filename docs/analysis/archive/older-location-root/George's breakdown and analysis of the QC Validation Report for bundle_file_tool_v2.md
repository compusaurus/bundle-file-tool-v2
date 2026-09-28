Here is a breakdown and analysis of the **QC Validation Report** for bundle\_file\_tool\_v2:

### **Executive Summary**

* **Overall Status:** **FAILED ✗**  
* **Total Issues:** 135 (14 Errors, 120 Warnings, 1 Info, 0 Blockers)  
* **Files Affected:** 15 of 24 checked

### **1\. Errors (14 Total) — Primary Causes for Failure**

The 14 errors fall into two distinct categories:

#### **A. Validator Scope Collision on Built-in set() (13 Errors)**

* **Problem:** 13 of the 14 errors flag calls to Python’s built-in set() or set(iterable) as signature mismatches against the custom method set(self, key, value) defined in src/core/config.py:277.  
* **Affected Locations:**  
  * src/core/models.py (Line 140\) — set(...) (1 arg vs expected 2\)  
  * scripts/code\_catalog\_comparison\_v3\_3.py (Lines 79, 90, 186\) — 5 instances  
  * src/database/schema\_ids.py (Line 842\) — set() (0 args vs expected 2\)  
  * src/core/config.py (Line 206\) — set() (0 args vs expected 2\)  
  * src/core/validators.py (Line 256\) — set() (0 args vs expected 2\)  
  * src/core/writer.py (Lines 118, 578\) — set() (0 args vs expected 2\)  
  * src/core/profiles/plain\_marker.py (Lines 292, 459\) — set() (0 args vs expected 2\)  
* **Diagnosis:** This is a **static analyzer / symbol resolution issue** in the QC validation engine. It is resolving built-in set instantiation to the Config.set method symbol because of unqualified name matching.

#### **B. Real Function Signature Mismatch (1 Error)**

* **Location:** src/cli.py (Line 241\)  
* **Target Definition:** assert\_bundle\_clean at src/core/bundle\_integrity.py:112  
* **Mismatch:** The call in cli.py passes 2 arguments (1 positional, 1 keyword), but bundle\_integrity.py expects 1 parameter.

### **2\. Warnings (120 Total)**

#### **A. Class Name Collision (1 Warning)**

* **Class:** PlainMarkerProfile  
* **Files:**  
  * updates/Proposed\_plain\_marker.py (staging/proposed file)  
  * src/core/profiles/plain\_marker.py (production module)  
* **Remediation:** Remove or archive the updates/ staging script from the active validation scan path, or rename the staging class.

#### **B. Potential Orphan Assets (119 Warnings)**

All 119 warnings are triggered by orphan\_detection\_with\_call\_chain (assets with no incoming static call relationships). These are primarily dynamic entry points:

> 1. **AST Node Visitors (41 in scripts/code\_catalogger\_v3.py):** Standard ast.NodeVisitor methods (visit\_If, visit\_For, visit\_ClassDef, etc.) called dynamically via Python's AST dispatch rather than direct call chains.  
> 2. **UI Framework Methods (51 across src/ui/):** Tkinter/GUI event callbacks, UI layout constructors (\_create\_action\_bar, \_on\_selection\_change, menu\_\*, open\_bundle), and AppMode enum members in bundle\_frame.py, main\_window.py, unbundle\_frame.py, and mode\_manager.py.  
> 3. **Standalone Script Entry Points (27 across scripts/):** Helper functions in code\_catalog\_comparison\_v3\_3.py and code\_catalogger\_v3.py.  
* **Remediation:** Annotate these methods/classes as entry points or ignore dynamic dispatch patterns in the QC manifest configuration.

### **3\. Informational (1 Total)**

* splash\_relationship\_validation: Context lacks explicit PROFILE\_\* relationship graph data.

### **Recommended Action Plan**

> 1. **Fix the CLI Signature Mismatch (src/cli.py:241):** Reconcile the arguments passed to assert\_bundle\_clean with its definition in src/core/bundle\_integrity.py.  
> 2. **Update QC Rule / Symbol Resolver:** Exclude Python built-in symbols (such as set, list, dict, tuple, str, int) from global custom function signature matching in the validator engine.  
> 3. **Clean up updates/ Directory:** Exclude staging/scratch directories from the QC runner to eliminate the duplicate class collision.  
> 4. **Update Manifest / Entry Points:** Whitelist AST visitor methods (visit\_\*) and Tkinter UI handler methods as known dynamic entry points.

Please let me know if you would like me to draft fixes for the cli.py call mismatch, inspect any of the specific files, or assist with refining the QC validator rules.