/*! NodeThermX Web v0.3.0 | MIT License | https://www.npmjs.com/package/nodethermx */
(function (global) {
  "use strict";
  const api = (function () {
    const modules = Object.create(null);
    modules["./thermometer_fields"] = function (module, exports, require) {
      /**
       * NodeThermX JSON field and enum value constants.
       *
       * Governance intent:
       * - Avoid scattered string literals.
       * - Maintain exact parity with PyThermX schema definitions.
       * - Keep schema evolution additive.
       */
      
      
      "use strict";
      
      
      const CONFIG_VERSION_V1_0 = "1.0";
      
      
      // Dict keys: State document (v1.0)
      const ST_STATE_VERSION = "state_version";
      const ST_MODE = "mode";
      const ST_CURRENT = "current";
      const ST_TOTAL = "total";
      const ST_PERCENT = "percent";
      const ST_LABEL = "label";
      const ST_UNIT = "unit";
      const ST_PHASE = "phase";
      const ST_ELAPSED_S = "elapsed_s";
      const ST_PROMOTED_FROM = "promoted_from";
      
      
      // Cancellation telemetry (v1.1)
      const ST_CANCELLATION_STATE = "cancellation_state";
      const ST_TERMINAL_OUTCOME = "terminal_outcome";
      
      
      // Enum values: Mode
      const MODE_DETERMINATE = "determinate";
      const MODE_INDETERMINATE = "indeterminate";
      
      
      // Schema versions
      const STATE_VERSION_V1_0 = "1.0";
      const STATE_VERSION_V1_1 = "1.1";
      
      
      // Status constants
      const STATUS_IDLE = "idle";
      const STATUS_RUNNING = "running";
      const STATUS_COMPLETE = "complete";
      const STATUS_ERROR = "error";
      
      
      module.exports = {
        CONFIG_VERSION_V1_0,
        ST_STATE_VERSION,
        ST_MODE,
        ST_CURRENT,
        ST_TOTAL,
        ST_PERCENT,
        ST_LABEL,
        ST_UNIT,
        ST_PHASE,
        ST_ELAPSED_S,
        ST_PROMOTED_FROM,
        ST_CANCELLATION_STATE,
        ST_TERMINAL_OUTCOME,
        MODE_DETERMINATE,
        MODE_INDETERMINATE,
        STATE_VERSION_V1_0,
        STATE_VERSION_V1_1,
        STATUS_IDLE,
        STATUS_RUNNING,
        STATUS_COMPLETE,
        STATUS_ERROR,
      };
    };
    
    modules["./thermometer_core"] = function (module, exports, require) {
      /**
       * UI-agnostic progress state machine for determinate and indeterminate work.
       */
      
      
      "use strict";
      
      
      const { MODE_DETERMINATE, MODE_INDETERMINATE } = require("./thermometer_fields");
      
      
      /**
       * Validate that value is a finite number, strictly rejecting booleans, non-numbers,
       * NaN, +Infinity, and -Infinity.
       */
      function sanitizeFinite(value, what = "value") {
        if (typeof value !== "number" || typeof value === "boolean") {
          throw new TypeError(`${what} must be a number, got ${typeof value}`);
        }
        if (!Number.isFinite(value)) {
          throw new RangeError(`${what} must be a finite number, got ${value}`);
        }
        return value;
      }
      
      
      /**
       * Validate that value is a finite number >= 0.
       */
      function sanitizeNonNegative(value, what = "value") {
        const num = sanitizeFinite(value, what);
        if (num < 0) {
          throw new RangeError(`${what} cannot be negative, got ${num}`);
        }
        return num;
      }
      
      
      /**
       * Immutable snapshot of progress state.
       */
      class ThermometerState {
        constructor(current, total, percent, label = null, mode = MODE_DETERMINATE, unit = null, phase = null, elapsed_s = 0.0, promoted_from = null) {
          this.current = current;
          this.total = total;
          this.percent = percent;
          this.label = label;
          this.mode = mode;
          this.unit = unit;
          this.phase = phase;
          this.elapsed_s = elapsed_s;
          this.promoted_from = promoted_from;
          Object.freeze(this);
        }
      }
      
      
      /**
       * Default clock: monotonic seconds via process.hrtime.bigint()
       */
      function defaultClock() {
        const ns = process.hrtime.bigint();
        return Number(ns) / 1_000_000_000;
      }
      
      
      class ThermometerCore {
        /**
         * Supports both:
         *   new ThermometerCore(total, label, { unit, phase, clock })
         *   new ThermometerCore({ total, label, unit, phase, clock })
         */
        constructor(totalArg = null, labelArg = null, options = {}) {
          let total = totalArg;
          let label = labelArg;
          let unit = null;
          let phase = null;
          let clock = defaultClock;
      
      
          if (totalArg !== null && typeof totalArg === "object" && !(totalArg instanceof Number)) {
            total = totalArg.total ?? null;
            label = totalArg.label ?? null;
            unit = totalArg.unit ?? null;
            phase = totalArg.phase ?? null;
            clock = totalArg.clock ?? defaultClock;
          } else {
            if (options && typeof options === "object") {
              unit = options.unit ?? null;
              phase = options.phase ?? null;
              clock = options.clock ?? defaultClock;
            }
          }
      
      
          if (typeof clock !== "function") {
            throw new TypeError("clock must be a function returning seconds");
          }
          this._clock = clock;
      
      
          if (total !== null && total !== undefined) {
            const totalNum = sanitizeFinite(total, "total");
            if (totalNum <= 0) {
              throw new RangeError("total must be > 0");
            }
            this._total = totalNum;
            this._mode = MODE_DETERMINATE;
          } else {
            this._total = null;
            this._mode = MODE_INDETERMINATE;
          }
      
      
          this._current = 0.0;
          this._label = label !== undefined ? label : null;
          this._unit = unit !== undefined ? unit : null;
          this._phase = phase !== undefined ? phase : null;
          this._promoted_from = null;
      
      
          const startedReading = sanitizeFinite(this._clock(), "the clock reading");
          this._started_at = startedReading;
        }
      
      
        get mode() { return this._mode; }
        get total() { return this._total; }
        get current() { return this._current; }
        get percent() {
          if (this._total === null) return null;
          return (this._current / this._total) * 100.0;
        }
        get label() { return this._label; }
        get unit() { return this._unit; }
        get phase() { return this._phase; }
        get promoted_from() { return this._promoted_from; }
        get promotedFrom() { return this._promoted_from; }
      
      
        get elapsed_s() {
          const now = sanitizeFinite(this._clock(), "the clock reading");
          return Math.max(0.0, now - this._started_at);
        }
      
      
        set_total(total) {
          if (this._mode === MODE_INDETERMINATE) {
            throw new Error("cannot set a total in indeterminate mode; use promote()");
          }
          const totalNum = sanitizeFinite(total, "total");
          if (totalNum <= 0) {
            throw new RangeError("total must be > 0");
          }
          this._total = totalNum;
          if (this._current > this._total) {
            this._current = this._total;
          }
        }
        setTotal(total) { return this.set_total(total); }
      
      
        set_label(label) { this._label = label ?? null; }
        setLabel(label) { return this.set_label(label); }
      
      
        set_unit(unit) { this._unit = unit ?? null; }
        setUnit(unit) { return this.set_unit(unit); }
      
      
        set_phase(phase) { this._phase = phase ?? null; }
        setPhase(phase) { return this.set_phase(phase); }
      
      
        update(value) {
          const val = sanitizeNonNegative(value, "current value");
          this._current = this._total === null ? val : Math.min(val, this._total);
        }
      
      
        increment(delta = 1.0) {
          const d = sanitizeNonNegative(delta, "delta");
          const next = this._current + d;
          this._current = this._total === null ? next : Math.min(next, this._total);
        }
      
      
        promote(total, options = {}) {
          if (this._mode !== MODE_INDETERMINATE) {
            throw new Error("only indeterminate progress can be promoted");
          }
          const totalNum = sanitizeFinite(total, "total");
          if (totalNum <= 0) {
            throw new RangeError("total must be > 0");
          }
      
      
          let currentVal = 0.0;
          let phaseVal = null;
          if (options && typeof options === "object") {
            if (options.current !== undefined && options.current !== null) {
              currentVal = sanitizeNonNegative(options.current, "current value");
            }
            if (options.phase !== undefined) {
              phaseVal = options.phase;
            }
          }
      
      
          this._promoted_from = this._current;
          this._total = totalNum;
          this._current = Math.min(currentVal, this._total);
          this._mode = MODE_DETERMINATE;
          if (phaseVal !== null && phaseVal !== undefined) {
            this._phase = phaseVal;
          }
        }
      
      
        reset() {
          this._current = 0.0;
          this._promoted_from = null;
          this._started_at = sanitizeFinite(this._clock(), "the clock reading");
        }
      
      
        snapshot() {
          return new ThermometerState(
            this._current,
            this._total,
            this.percent,
            this._label,
            this._mode,
            this._unit,
            this._phase,
            this.elapsed_s,
            this._promoted_from
          );
        }
      }
      
      
      module.exports = {
        ThermometerCore,
        ThermometerState,
        sanitizeFinite,
        sanitizeNonNegative,
        defaultClock,
      };
    };
    
    modules["./cancellation"] = function (module, exports, require) {
      /**
       * Cooperative cancellation for NodeThermX.
       *
       * NodeThermX observes work; it does not own it.
       * NodeThermX never forcefully aborts, terminates, or kills a worker.
       * It supplies a cooperative protocol between requester and worker.
       */
      
      
      "use strict";
      
      
      const { sanitizeFinite, sanitizeNonNegative } = require("./thermometer_core");
      
      
      const CancellationState = Object.freeze({
        ACTIVE: "active",
        REQUESTED: "requested",
        CANCELLING: "cancelling",
        CANCELLED: "cancelled",
      });
      
      
      const TerminalOutcome = Object.freeze({
        COMPLETED: "completed",
        FAILED: "failed",
        CANCELLED: "cancelled",
      });
      
      
      class CancellationRequestedError extends Error {
        constructor(message = "cancellation was requested") {
          super(message);
          this.name = "CancellationRequestedError";
        }
      }
      
      
      class CancellationStateError extends Error {
        constructor(message) {
          super(message);
          this.name = "CancellationStateError";
        }
      }
      
      
      /**
       * Immutable snapshot of cancellation telemetry.
       */
      class CancellationStatus {
        constructor(state) {
          this.state = state;
          this.isRequested = state !== CancellationState.ACTIVE;
          this.is_requested = this.isRequested;
          this.isTerminal = state === CancellationState.CANCELLED;
          this.is_terminal = this.isTerminal;
          this.wireValue = state;
          this.wire_value = state;
          Object.freeze(this);
        }
      }
      
      
      const ACTIVE_STATUS = new CancellationStatus(CancellationState.ACTIVE);
      
      
      /**
       * Strict timeout validator for wait()
       */
      function validateTimeout(value) {
        if (value === null || value === undefined) {
          return null;
        }
        if (typeof value === "boolean") {
          throw new TypeError(`timeout must be a real number or null, got bool ${value}`);
        }
        if (typeof value !== "number") {
          throw new TypeError(`timeout must be a real number or null, got ${typeof value} ${value}`);
        }
        if (!Number.isFinite(value)) {
          throw new RangeError(`timeout must be a finite number, got ${value}`);
        }
        if (value < 0) {
          throw new RangeError(`timeout cannot be negative, got ${value}`);
        }
        return value;
      }
      
      
      class CancellationToken {
        constructor(source) {
          if (!source || !(source instanceof CancellationSource)) {
            throw new TypeError(
              "a CancellationToken is obtained from CancellationSource.token, not constructed directly"
            );
          }
          this._source = source;
        }
      
      
        get isRequested() { return this._source.isRequested; }
        get is_requested() { return this._source.isRequested; }
      
      
        get state() { return this._source.state; }
        get status() { return this._source.status; }
      
      
        async wait(timeout) {
          return this._source.waitForCancellation(timeout);
        }
      
      
        throwIfRequested() {
          if (this.isRequested) {
            throw new CancellationRequestedError();
          }
        }
        raise_if_requested() { return this.throwIfRequested(); }
      
      
        acknowledge() {
          return this._source._advance(CancellationState.CANCELLING, "acknowledge");
        }
      
      
        complete() {
          return this._source._advance(CancellationState.CANCELLED, "complete");
        }
      }
      
      
      class CancellationSource {
        constructor() {
          this._state = CancellationState.ACTIVE;
          this._token = new CancellationToken(this);
          this._waiters = new Set();
        }
      
      
        get token() { return this._token; }
        get state() { return this._state; }
        get isRequested() { return this._state !== CancellationState.ACTIVE; }
        get is_requested() { return this.isRequested; }
      
      
        get status() {
          if (this._state === CancellationState.ACTIVE) {
            return ACTIVE_STATUS;
          }
          return new CancellationStatus(this._state);
        }
      
      
        request() {
          if (this._state !== CancellationState.ACTIVE) {
            return false;
          }
          this._state = CancellationState.REQUESTED;
          for (const resolve of this._waiters) {
            resolve(true);
          }
          this._waiters.clear();
          return true;
        }
      
      
        waitForCancellation(timeout = null) {
          const validTimeout = validateTimeout(timeout);
      
      
          if (this.isRequested) {
            return Promise.resolve(true);
          }
      
      
          if (validTimeout !== null) {
            if (validTimeout === 0) {
              return Promise.resolve(this.isRequested);
            }
      
      
            // Convert seconds/milliseconds if given in seconds or ms
            // Standard: timeout in seconds (matching PyThermX) or milliseconds.
            // If validTimeout is float in seconds (e.g. 0.05) or ms, we convert seconds to ms
            // Rule: timeout is interpreted in seconds when float < 1000 or explicitly seconds.
            // To ensure parity with Python wait(0.05), we treat numbers as seconds:
            const ms = validTimeout * 1000;
      
      
            return new Promise((resolve) => {
              let timer = null;
              const cb = (val) => {
                if (timer) clearTimeout(timer);
                this._waiters.delete(cb);
                resolve(val);
              };
              timer = setTimeout(() => {
                this._waiters.delete(cb);
                resolve(this.isRequested);
              }, ms);
              if (timer.unref) timer.unref();
              this._waiters.add(cb);
            });
          }
      
      
          return new Promise((resolve) => {
            this._waiters.add(resolve);
          });
        }
      
      
        _advance(target, callerName) {
          if (this._state === CancellationState.ACTIVE) {
            throw new CancellationStateError(
              `cannot ${callerName}() a cancellation that was never requested; ` +
              `the worker's half of the protocol only becomes available after CancellationSource.request()`
            );
          }
      
      
          if (this._state === target) {
            return false;
          }
      
      
          const legalTransitions = {
            [CancellationState.REQUESTED]: [CancellationState.CANCELLING, CancellationState.CANCELLED],
            [CancellationState.CANCELLING]: [CancellationState.CANCELLED],
            [CancellationState.CANCELLED]: [],
          };
      
      
          const allowed = legalTransitions[this._state] || [];
          if (!allowed.includes(target)) {
            throw new CancellationStateError(
              `cannot ${callerName}(): ${this._state} does not advance to ${target}`
            );
          }
      
      
          this._state = target;
          return true;
        }
      }
      
      
      class AbortSignalBridge {
        static fromAbortSignal(signal) {
          const source = new CancellationSource();
          if (!signal) return source;
          if (signal.aborted) {
            source.request();
          } else {
            signal.addEventListener("abort", () => source.request(), { once: true });
          }
          return source;
        }
      
      
        static toAbortSignal(token) {
          const controller = new AbortController();
          if (token.isRequested) {
            controller.abort();
          } else {
            token.wait().then(() => controller.abort()).catch(() => {});
          }
          return controller.signal;
        }
      }
      
      
      module.exports = {
        CancellationState,
        TerminalOutcome,
        CancellationRequestedError,
        CancellationStateError,
        CancellationStatus,
        ACTIVE_STATUS,
        CancellationToken,
        CancellationSource,
        AbortSignalBridge,
        validateTimeout,
      };
    };
    
    modules["./serialization"] = function (module, exports, require) {
      /**
       * JSON-ready serialization and wire validation for NodeThermX.
       */
      
      
      "use strict";
      
      
      const { sanitizeFinite, sanitizeNonNegative, ThermometerState } = require("./thermometer_core");
      const {
        CancellationState,
        TerminalOutcome,
        CancellationStatus,
        ACTIVE_STATUS,
      } = require("./cancellation");
      const {
        ST_STATE_VERSION,
        ST_MODE,
        ST_CURRENT,
        ST_TOTAL,
        ST_PERCENT,
        ST_LABEL,
        ST_UNIT,
        ST_PHASE,
        ST_ELAPSED_S,
        ST_PROMOTED_FROM,
        ST_CANCELLATION_STATE,
        ST_TERMINAL_OUTCOME,
        MODE_DETERMINATE,
        MODE_INDETERMINATE,
        STATE_VERSION_V1_0,
        STATE_VERSION_V1_1,
      } = require("./thermometer_fields");
      
      
      const STATE_KEYS_V1_0 = new Set([
        ST_STATE_VERSION,
        ST_MODE,
        ST_CURRENT,
        ST_TOTAL,
        ST_PERCENT,
        ST_LABEL,
        ST_UNIT,
        ST_PHASE,
        ST_ELAPSED_S,
        ST_PROMOTED_FROM,
      ]);
      
      
      const STATE_KEYS_V1_1 = new Set([
        ...STATE_KEYS_V1_0,
        ST_CANCELLATION_STATE,
        ST_TERMINAL_OUTCOME,
      ]);
      
      
      const STATE_KEYS = STATE_KEYS_V1_0;
      const SUPPORTED_STATE_MAJOR = 1;
      
      
      const PERCENT_REL_TOL = 1e-12;
      const PERCENT_ABS_TOL = 1e-12;
      
      
      class UnsupportedStateVersionError extends Error {
        constructor(message) {
          super(message);
          this.name = "UnsupportedStateVersionError";
        }
      }
      
      
      class ProgressEnvelope {
        constructor(state, cancellation = ACTIVE_STATUS, terminalOutcome = null) {
          if (typeof state === "object" && !(state instanceof ThermometerState) && state.state) {
            this.state = state.state;
            this.cancellation = state.cancellation ?? ACTIVE_STATUS;
            this.terminal_outcome = state.terminal_outcome ?? state.terminalOutcome ?? null;
            this.terminalOutcome = this.terminal_outcome;
          } else {
            this.state = state;
            this.cancellation = cancellation ?? ACTIVE_STATUS;
            this.terminal_outcome = terminalOutcome ?? null;
            this.terminalOutcome = this.terminal_outcome;
          }
          Object.freeze(this);
        }
      }
      
      
      function isClose(a, b, relTol = PERCENT_REL_TOL, absTol = PERCENT_ABS_TOL) {
        return Math.abs(a - b) <= Math.max(relTol * Math.max(Math.abs(a), Math.abs(b)), absTol);
      }
      
      
      function parseStateVersion(document) {
        const raw = document[ST_STATE_VERSION] !== undefined ? document[ST_STATE_VERSION] : STATE_VERSION_V1_0;
        if (typeof raw !== "string") {
          throw new UnsupportedStateVersionError(`state_version must be a string, got ${typeof raw}`);
        }
        const match = /^(\d+)\.(\d+)$/.exec(raw);
        if (!match) {
          throw new UnsupportedStateVersionError(`malformed state_version ${JSON.stringify(raw)}`);
        }
        const major = parseInt(match[1], 10);
        const minor = parseInt(match[2], 10);
        if (major !== SUPPORTED_STATE_MAJOR) {
          throw new UnsupportedStateVersionError(
            `unsupported state_version ${JSON.stringify(raw)}; this build supports ${SUPPORTED_STATE_MAJOR}.x`
          );
        }
        return { major, minor };
      }
      
      
      const LEGAL_OUTCOMES = {
        [CancellationState.ACTIVE]: [null, TerminalOutcome.COMPLETED, TerminalOutcome.FAILED],
        [CancellationState.REQUESTED]: [null, TerminalOutcome.COMPLETED, TerminalOutcome.FAILED],
        [CancellationState.CANCELLING]: [null, TerminalOutcome.FAILED],
        [CancellationState.CANCELLED]: [TerminalOutcome.CANCELLED],
      };
      
      
      function validateCancellation(document) {
        const stateRaw = document[ST_CANCELLATION_STATE];
        if (typeof stateRaw !== "string" || !Object.values(CancellationState).includes(stateRaw)) {
          throw new RangeError(`expected valid cancellation_state, got ${JSON.stringify(stateRaw)}`);
        }
        const outcomeRaw = document[ST_TERMINAL_OUTCOME];
        if (outcomeRaw !== null && (typeof outcomeRaw !== "string" || !Object.values(TerminalOutcome).includes(outcomeRaw))) {
          throw new RangeError(`expected valid terminal_outcome or null, got ${JSON.stringify(outcomeRaw)}`);
        }
      
      
        const allowed = LEGAL_OUTCOMES[stateRaw] || [];
        if (!allowed.includes(outcomeRaw)) {
          throw new Error(
            `${JSON.stringify(outcomeRaw)} is not a legal outcome while cancellation_state is ${JSON.stringify(stateRaw)}`
          );
        }
      }
      
      
      function validateDocument(document) {
        if (typeof document !== "object" || document === null || Array.isArray(document)) {
          throw new TypeError(`expected an object mapping, got ${typeof document}`);
        }
      
      
        const { major, minor } = parseStateVersion(document);
        const required = minor === 0 ? STATE_KEYS_V1_0 : STATE_KEYS_V1_1;
      
      
        for (const k of required) {
          if (k === ST_STATE_VERSION) continue;
          if (!(k in document)) {
            throw new Error(`document missing required key: ${k}`);
          }
        }
      
      
        const mode = document[ST_MODE];
        if (mode !== MODE_DETERMINATE && mode !== MODE_INDETERMINATE) {
          throw new RangeError(`expected valid mode, got ${JSON.stringify(mode)}`);
        }
      
      
        const current = sanitizeNonNegative(document[ST_CURRENT], ST_CURRENT);
        const elapsed = sanitizeNonNegative(document[ST_ELAPSED_S], ST_ELAPSED_S);
      
      
        for (const field of [ST_LABEL, ST_UNIT, ST_PHASE]) {
          const v = document[field];
          if (v !== null && typeof v !== "string") {
            throw new TypeError(`${field}: expected a string or null, got ${typeof v}`);
          }
        }
      
      
        const total = document[ST_TOTAL];
        const percent = document[ST_PERCENT];
      
      
        if (mode === MODE_INDETERMINATE) {
          if (total !== null) throw new Error(`${ST_TOTAL}: must be null in indeterminate mode`);
          if (percent !== null) throw new Error(`${ST_PERCENT}: must be null in indeterminate mode`);
        } else {
          if (total === null) throw new Error(`${ST_TOTAL}: must not be null in determinate mode`);
          if (percent === null) throw new Error(`${ST_PERCENT}: must not be null in determinate mode`);
          const totalNum = sanitizeFinite(total, ST_TOTAL);
          const percentNum = sanitizeFinite(percent, ST_PERCENT);
      
      
          if (totalNum <= 0) throw new RangeError(`${ST_TOTAL}: must be > 0`);
          if (current > totalNum) throw new RangeError(`${ST_CURRENT}: must be <= total (${current} > ${totalNum})`);
          if (percentNum < 0 || percentNum > 100) throw new RangeError(`${ST_PERCENT}: must be within 0..100`);
      
      
          const expected = (current / totalNum) * 100.0;
          if (!isClose(percentNum, expected)) {
            throw new Error(`${ST_PERCENT}: ${percentNum} is not coherent with current/total (${expected})`);
          }
        }
      
      
        if (document[ST_PROMOTED_FROM] !== null) {
          sanitizeNonNegative(document[ST_PROMOTED_FROM], ST_PROMOTED_FROM);
        }
      
      
        if (minor >= 1) {
          validateCancellation(document);
        }
      
      
        return { major, minor };
      }
      
      
      function toDict(state) {
        const doc = {
          [ST_STATE_VERSION]: STATE_VERSION_V1_0,
          [ST_MODE]: state.mode,
          [ST_CURRENT]: Number(state.current),
          [ST_TOTAL]: state.total === null ? null : Number(state.total),
          [ST_PERCENT]: state.percent === null ? null : Number(state.percent),
          [ST_LABEL]: state.label,
          [ST_UNIT]: state.unit,
          [ST_PHASE]: state.phase,
          [ST_ELAPSED_S]: Number(state.elapsed_s),
          [ST_PROMOTED_FROM]: state.promoted_from === null ? null : Number(state.promoted_from),
        };
        validateDocument(doc);
        return doc;
      }
      
      
      function toJson(state, ...args) {
        if (args.length > 0 && typeof args[0] === "object" && args[0] !== null && "allow_nan" in args[0]) {
          throw new TypeError("allow_nan is reserved by toJson()");
        }
        return JSON.stringify(toDict(state));
      }
      
      
      function fromDict(document) {
        validateDocument(document);
        return new ThermometerState(
          Number(document[ST_CURRENT]),
          document[ST_TOTAL] === null ? null : Number(document[ST_TOTAL]),
          document[ST_PERCENT] === null ? null : Number(document[ST_PERCENT]),
          document[ST_LABEL],
          document[ST_MODE],
          document[ST_UNIT],
          document[ST_PHASE],
          Number(document[ST_ELAPSED_S]),
          document[ST_PROMOTED_FROM] === null ? null : Number(document[ST_PROMOTED_FROM])
        );
      }
      
      
      function envelopeToDict(envelope) {
        if (!envelope || !envelope.state) {
          throw new TypeError("expected a ProgressEnvelope");
        }
        const doc = toDict(envelope.state);
        doc[ST_STATE_VERSION] = STATE_VERSION_V1_1;
        const cStatus = envelope.cancellation || ACTIVE_STATUS;
        doc[ST_CANCELLATION_STATE] = cStatus.state;
        doc[ST_TERMINAL_OUTCOME] = envelope.terminal_outcome ?? envelope.terminalOutcome ?? null;
        validateDocument(doc);
        return doc;
      }
      
      
      function envelopeToJson(envelope, ...args) {
        if (args.length > 0 && typeof args[0] === "object" && args[0] !== null && "allow_nan" in args[0]) {
          throw new TypeError("allow_nan is reserved by envelopeToJson()");
        }
        return JSON.stringify(envelopeToDict(envelope));
      }
      
      
      function envelopeFromDict(document) {
        const { minor } = validateDocument(document);
        const state = fromDict(document);
        if (minor === 0) {
          return new ProgressEnvelope(state, ACTIVE_STATUS, null);
        }
        const cStatus = new CancellationStatus(document[ST_CANCELLATION_STATE]);
        const outcome = document[ST_TERMINAL_OUTCOME] ?? null;
        return new ProgressEnvelope(state, cStatus, outcome);
      }
      
      
      module.exports = {
        STATE_KEYS,
        STATE_KEYS_V1_0,
        STATE_KEYS_V1_1,
        SUPPORTED_STATE_MAJOR,
        PERCENT_REL_TOL,
        PERCENT_ABS_TOL,
        UnsupportedStateVersionError,
        ProgressEnvelope,
        toDict,
        to_dict: toDict,
        toJson,
        to_json: toJson,
        fromDict,
        from_dict: fromDict,
        envelopeToDict,
        envelope_to_dict: envelopeToDict,
        envelopeToJson,
        envelope_to_json: envelopeToJson,
        envelopeFromDict,
        envelope_from_dict: envelopeFromDict,
        validateDocument,
      };
    };
    
    modules["./presentation"] = function (module, exports, require) {
      /**
       * Browser-safe presentation primitives for NodeThermX snapshots and envelopes.
       *
       * This module formats semantic state but renders nothing. CLI, demos, React,
       * and other consumers can therefore share one vocabulary without sharing UI.
       */
      
      "use strict";
      
      
      const PRESENTATION_LEXICON_DEFAULTS = Object.freeze({
        ok: "OK",
        fail: "FAIL",
        cancelled: "CANCELLED",
        found: "found",
      });
      
      
      const PRESENTATION_FORMAT_DEFAULTS = Object.freeze({
        locale: "en-US",
        percent_precision: 1,
        show_percent: true,
        show_value: true,
        show_label: true,
        show_count: true,
        show_elapsed: false,
        show_rate: false,
        show_eta: false,
        count_format: "{:,.0f}",
        unit: null,
        promoted_separator: "-",
        value_separator: "/",
        field_separator: " | ",
        elapsed_suffix: "s",
        rate_suffix: "/s",
        eta_prefix: "ETA ",
        lexicon: PRESENTATION_LEXICON_DEFAULTS,
      });
      
      
      function freezeFormat(value) {
        if (value && typeof value === "object" && !Object.isFrozen(value)) {
          for (const child of Object.values(value)) freezeFormat(child);
          Object.freeze(value);
        }
        return value;
      }
      
      
      function createPresentationFormat(options = {}) {
        if (!options || typeof options !== "object" || Array.isArray(options)) {
          throw new TypeError("presentation format must be an object");
        }
        const precision = Number(options.percent_precision ?? options.percentPrecision ?? 1);
        const lexiconOptions = options.lexicon || {};
        const format = {
          locale: typeof options.locale === "string" && options.locale ? options.locale : "en-US",
          percent_precision: Number.isInteger(precision) && precision >= 0 && precision <= 20 ? precision : 1,
          show_percent: Boolean(options.show_percent ?? options.showPercent ?? true),
          show_value: Boolean(options.show_value ?? options.showValue ?? true),
          show_label: Boolean(options.show_label ?? options.showLabel ?? true),
          show_count: Boolean(options.show_count ?? options.showCount ?? true),
          show_elapsed: Boolean(options.show_elapsed ?? options.showElapsed ?? false),
          show_rate: Boolean(options.show_rate ?? options.showRate ?? false),
          show_eta: Boolean(options.show_eta ?? options.showEta ?? false),
          count_format: options.count_format ?? options.countFormat ?? "{:,.0f}",
          unit: options.unit ?? null,
          promoted_separator: String(options.promoted_separator ?? options.promotedSeparator ?? "-"),
          value_separator: String(options.value_separator ?? options.valueSeparator ?? "/"),
          field_separator: String(options.field_separator ?? options.fieldSeparator ?? " | "),
          elapsed_suffix: String(options.elapsed_suffix ?? options.elapsedSuffix ?? "s"),
          rate_suffix: String(options.rate_suffix ?? options.rateSuffix ?? "/s"),
          eta_prefix: String(options.eta_prefix ?? options.etaPrefix ?? "ETA "),
          lexicon: {
            ok: String(lexiconOptions.ok ?? "OK"),
            fail: String(lexiconOptions.fail ?? "FAIL"),
            cancelled: String(lexiconOptions.cancelled ?? "CANCELLED"),
            found: String(lexiconOptions.found ?? "found"),
          },
        };
        return freezeFormat(format);
      }
      
      
      function pythonStyleNumberFormat(value, pattern, locale) {
        const fixed = /^\{:(,)?\.(\d+)f\}$/.exec(pattern);
        if (fixed) {
          const digits = Number(fixed[2]);
          return new Intl.NumberFormat(locale, {
            useGrouping: Boolean(fixed[1]),
            minimumFractionDigits: digits,
            maximumFractionDigits: digits,
          }).format(value);
        }
        if (pattern === "{:g}" || pattern === "{}") return String(Number(value));
        return null;
      }
      
      
      function formatCount(value, format = PRESENTATION_FORMAT_DEFAULTS) {
        const formatter = format.count_format;
        if (typeof formatter === "function") return String(formatter(value));
        if (typeof formatter === "string") {
          const formatted = pythonStyleNumberFormat(value, formatter, format.locale || "en-US");
          if (formatted !== null) return formatted;
        }
        return Math.round(value).toLocaleString(format.locale || "en-US");
      }
      
      
      function extractInput(input) {
        if (!input || typeof input !== "object") {
          throw new TypeError("present() requires a snapshot or progress envelope");
        }
        const state = input.state && typeof input.state === "object" ? input.state : input;
        const cancellation = input.state ? input.cancellation : null;
        const terminalOutcome = input.state
          ? (input.terminal_outcome ?? input.terminalOutcome ?? null)
          : null;
        if (state.current === undefined || state.elapsed_s === undefined) {
          throw new TypeError("present() input is not a NodeThermX state");
        }
        return { state, cancellation, terminalOutcome };
      }
      
      
      function present(input, formatOptions = PRESENTATION_FORMAT_DEFAULTS, estimate = null) {
        const format = Object.isFrozen(formatOptions) && formatOptions.lexicon
          ? formatOptions
          : createPresentationFormat(formatOptions);
        const { state, cancellation, terminalOutcome } = extractInput(input);
        const indeterminate = state.total === null || state.percent === null || state.mode === "indeterminate";
        const unit = format.unit ?? state.unit ?? null;
        const unitSuffix = unit ? ` ${unit}` : "";
        const percent = indeterminate ? null : Math.max(0, Math.min(100, Number(state.percent)));
        const percentWidth = Math.max(3, format.percent_precision + 4);
        const valueText = indeterminate
          ? null
          : `${state.current}${format.value_separator}${state.total}`;
        const promotionText = !indeterminate && state.promoted_from !== null && state.promoted_from !== undefined
          ? `${formatCount(state.promoted_from, format)}${unitSuffix} ${format.lexicon.found}`
          : null;
        const promotedValueText = promotionText
          ? `${promotionText} ${format.promoted_separator} ${valueText}`
          : valueText;
        const elapsed = Number(state.elapsed_s);
        const estimatedRate = estimate && (estimate.rate_per_s ?? estimate.ratePerS);
        const rate = Number.isFinite(estimatedRate)
          ? Number(estimatedRate)
          : (elapsed > 0 ? Number(state.current) / elapsed : 0);
        const etaValue = estimate ? (estimate.eta_s ?? estimate.etaS) : null;
        const eta = etaValue === null || etaValue === undefined ? NaN : Number(etaValue);
        const lifecycle = cancellation
          ? (cancellation.state ?? cancellation.wire_value ?? cancellation.wireValue ?? null)
          : null;
      
        return Object.freeze({
          mode: indeterminate ? "indeterminate" : "determinate",
          indeterminate,
          fraction: indeterminate ? null : percent / 100,
          percentText: !indeterminate && format.show_percent
            ? `${percent.toFixed(format.percent_precision).padStart(percentWidth, " ")}%`
            : null,
          valueText: format.show_value ? valueText : null,
          promotionText: format.show_value ? promotionText : null,
          promotedValueText: format.show_value ? promotedValueText : null,
          countText: format.show_count ? `${formatCount(Number(state.current), format)}${unitSuffix}` : null,
          labelText: format.show_label ? (state.phase || state.label || null) : null,
          elapsedText: format.show_elapsed
            ? `${elapsed.toFixed(format.percent_precision)}${format.elapsed_suffix}`
            : null,
          rateText: format.show_rate && elapsed > 0
            ? `${formatCount(rate, format)}${unit ? ` ${unit}${format.rate_suffix}` : format.rate_suffix}`
            : null,
          etaText: format.show_eta && Number.isFinite(eta)
            ? `${format.eta_prefix}${eta.toFixed(format.percent_precision)}${format.elapsed_suffix}`
            : null,
          unitText: unit,
          lifecycle,
          terminalOutcome,
        });
      }
      
      
      module.exports = {
        PRESENTATION_FORMAT_DEFAULTS,
        PRESENTATION_LEXICON_DEFAULTS,
        createPresentationFormat,
        formatCount,
        present,
      };
    };
    
    modules["./web_thermometer"] = function (module, exports, require) {
      /**
       * Lightweight, framework-free DOM renderer for ThermX progress documents.
       *
       * Transport and job policy stay with the application. This module validates
       * one state at a time and projects it onto a native <progress> element.
       */
      
      "use strict";
      
      
      const {
        ProgressEnvelope,
        envelopeFromDict,
        envelopeToDict,
        toDict,
      } = require("./serialization");
      const { createPresentationFormat, present } = require("./presentation");
      
      
      const WEB_LABEL_DEFAULTS = deepFreeze({
        progress: "Progress",
        idle: "Idle",
        active: "In progress",
        unknown: "Unknown total",
        promoted: "Total discovered",
        requested: "Cancellation requested",
        cancelling: "Cancelling",
        completed: "Completed",
        failed: "Failed",
        cancelled: "Cancelled",
        cancel: "Cancel",
      });
      
      
      const OPTION_KEYS = new Set([
        "cancellable",
        "onCancel",
        "onError",
        "presentation",
        "labels",
        "announce",
        "showDetails",
      ]);
      const LABEL_KEYS = new Set(Object.keys(WEB_LABEL_DEFAULTS));
      const HOST_STATE_ATTRIBUTES = Object.freeze([
        "data-thermx-state",
        "data-thermx-mode",
        "data-thermx-lifecycle",
        "data-thermx-outcome",
        "data-thermx-promoted",
        "aria-busy",
      ]);
      const PROGRESS_ATTRIBUTES = Object.freeze([
        "max",
        "value",
        "aria-label",
        "aria-labelledby",
        "aria-valuemin",
        "aria-valuemax",
        "aria-valuenow",
        "aria-valuetext",
      ]);
      const STATUS_ATTRIBUTES = Object.freeze(["role", "aria-live", "aria-atomic"]);
      const CANCEL_ATTRIBUTES = Object.freeze(["type", "aria-disabled"]);
      const INSTANCES = new WeakMap();
      const ATTACH_TOKEN = Symbol("NodeThermX.WebThermometer.attach");
      let labelSequence = 0;
      
      
      function deepFreeze(value) {
        if (value && typeof value === "object" && !Object.isFrozen(value)) {
          for (const child of Object.values(value)) deepFreeze(child);
          Object.freeze(value);
        }
        return value;
      }
      
      
      function hasOwn(value, key) {
        return Object.prototype.hasOwnProperty.call(value, key);
      }
      
      
      function assertElement(value, name) {
        if (!value || typeof value !== "object" || value.nodeType !== 1 || typeof value.setAttribute !== "function") {
          throw new TypeError(`${name} must be a DOM Element`);
        }
        return value;
      }
      
      
      function assertProgressElement(value, name = "progress") {
        const element = assertElement(value, name);
        if (String(element.tagName || "").toLowerCase() !== "progress") {
          throw new TypeError(`${name} must be a native <progress> element`);
        }
        return element;
      }
      
      
      function resolveLabels(input) {
        if (input === undefined) return WEB_LABEL_DEFAULTS;
        if (!input || typeof input !== "object" || Array.isArray(input)) {
          throw new TypeError("labels must be an object");
        }
        for (const key of Object.keys(input)) {
          if (!LABEL_KEYS.has(key)) throw new TypeError(`unknown web label: ${key}`);
          if (typeof input[key] !== "string" || !input[key]) {
            throw new TypeError(`labels.${key} must be a non-empty string`);
          }
        }
        return deepFreeze({ ...WEB_LABEL_DEFAULTS, ...input });
      }
      
      
      function resolveOptions(input = {}) {
        if (!input || typeof input !== "object" || Array.isArray(input)) {
          throw new TypeError("WebThermometer options must be an object");
        }
        for (const key of Object.keys(input)) {
          if (!OPTION_KEYS.has(key)) throw new TypeError(`unknown WebThermometer option: ${key}`);
        }
        if (input.cancellable !== undefined && typeof input.cancellable !== "boolean") {
          throw new TypeError("cancellable must be a boolean");
        }
        if (input.showDetails !== undefined && typeof input.showDetails !== "boolean") {
          throw new TypeError("showDetails must be a boolean");
        }
        for (const callback of ["onCancel", "onError"]) {
          if (input[callback] !== undefined && input[callback] !== null && typeof input[callback] !== "function") {
            throw new TypeError(`${callback} must be a function or null`);
          }
        }
        const announce = input.announce ?? "polite";
        if (announce !== "polite" && announce !== "off") {
          throw new RangeError('announce must be "polite" or "off"');
        }
        return Object.freeze({
          cancellable: input.cancellable ?? false,
          onCancel: input.onCancel ?? null,
          onError: input.onError ?? null,
          presentation: createPresentationFormat(input.presentation || {}),
          labels: resolveLabels(input.labels),
          announce,
          showDetails: input.showDetails ?? true,
        });
      }
      
      
      function normalizeProgressInput(input) {
        if (!input || typeof input !== "object" || Array.isArray(input)) {
          throw new TypeError("render() requires a progress document, envelope, or snapshot");
        }
      
        if (input.state && typeof input.state === "object") {
          const document = envelopeToDict(new ProgressEnvelope(
            input.state,
            input.cancellation,
            input.terminal_outcome ?? input.terminalOutcome ?? null
          ));
          return envelopeFromDict(document);
        }
      
        if (hasOwn(input, "mode") && hasOwn(input, "current") && hasOwn(input, "elapsed_s")) {
          if (hasOwn(input, "state_version") || hasOwn(input, "cancellation_state")) {
            return envelopeFromDict(input);
          }
          try {
            return envelopeFromDict(input);
          } catch (error) {
            // A live ThermometerState is not a wire mapping, but serializing it
            // supplies the canonical v1.0 version field and performs the same checks.
            return envelopeFromDict(toDict(input));
          }
        }
      
        throw new TypeError("render() input is not a ThermX progress value");
      }
      
      
      function createElement(document, tag, className = "") {
        const element = document.createElement(tag);
        if (className) element.className = className;
        return element;
      }
      
      
      function createCanonicalElements(host, options) {
        const document = host.ownerDocument;
        if (!document || typeof document.createElement !== "function") {
          throw new TypeError("host must belong to a document that can create elements");
        }
      
        const root = createElement(document, "div", "thermx");
        root.setAttribute("data-thermx-root", "");
        const heading = createElement(document, "div", "thermx__heading");
        const label = createElement(document, "span", "thermx__label");
        const percent = createElement(document, "span", "thermx__percent");
        percent.setAttribute("aria-hidden", "true");
        heading.appendChild(label);
        heading.appendChild(percent);
      
        const progress = createElement(document, "progress", "thermx__progress");
        progress.setAttribute("max", "100");
        const footer = createElement(document, "div", "thermx__footer");
        const detail = createElement(document, "span", "thermx__detail");
        const status = createElement(document, "span", "thermx__status");
        footer.appendChild(detail);
        footer.appendChild(status);
      
        const cancel = createElement(document, "button", "thermx__cancel");
        cancel.setAttribute("type", "button");
        cancel.textContent = options.labels.cancel;
      
        root.appendChild(heading);
        root.appendChild(progress);
        root.appendChild(footer);
        root.appendChild(cancel);
        host.appendChild(root);
        return { host, root, progress, label, percent, detail, status, cancel };
      }
      
      
      function normalizeAttachedElements(input, options) {
        if (!input || typeof input !== "object" || Array.isArray(input)) {
          throw new TypeError("WebThermometer.attach() requires an element map");
        }
        const host = assertElement(input.host, "elements.host");
        const progress = assertProgressElement(input.progress, "elements.progress");
        const result = {
          host,
          root: null,
          progress,
          label: input.label ? assertElement(input.label, "elements.label") : null,
          percent: input.percent ? assertElement(input.percent, "elements.percent") : null,
          detail: input.detail ? assertElement(input.detail, "elements.detail") : null,
          status: input.status ? assertElement(input.status, "elements.status") : null,
          cancel: input.cancel ? assertElement(input.cancel, "elements.cancel") : null,
        };
        const seen = new Set([host]);
        for (const [name, element] of Object.entries(result)) {
          if (name === "host" || name === "root" || !element) continue;
          if (seen.has(element)) throw new TypeError(`elements.${name} must be a distinct element`);
          seen.add(element);
          if (element.ownerDocument !== host.ownerDocument) {
            throw new TypeError(`elements.${name} must belong to the host document`);
          }
          if (typeof host.contains === "function" && !host.contains(element)) {
            throw new TypeError(`elements.${name} must be contained by elements.host`);
          }
        }
        if (options.cancellable && !result.cancel) {
          throw new TypeError("attached markup requires elements.cancel when cancellable is true");
        }
        return result;
      }
      
      
      function captureAttributes(element, names) {
        if (!element) return null;
        const attributes = {};
        for (const name of names) {
          attributes[name] = element.hasAttribute(name) ? element.getAttribute(name) : null;
        }
        return attributes;
      }
      
      
      function restoreAttributes(element, snapshot) {
        if (!element || !snapshot) return;
        for (const [name, value] of Object.entries(snapshot)) {
          if (value === null) element.removeAttribute(name);
          else element.setAttribute(name, value);
        }
      }
      
      
      function captureAttachedState(elements) {
        const states = new Map();
        const remember = (element, attributes, properties = []) => {
          if (!element || states.has(element)) return;
          const propertyValues = {};
          for (const property of properties) propertyValues[property] = element[property];
          states.set(element, {
            attributes: captureAttributes(element, attributes),
            properties: propertyValues,
            textContent: element.textContent,
          });
        };
        remember(elements.host, HOST_STATE_ATTRIBUTES);
        remember(elements.progress, PROGRESS_ATTRIBUTES, ["hidden"]);
        remember(elements.label, ["id"]);
        remember(elements.percent, ["aria-hidden"], ["hidden"]);
        remember(elements.detail, [], ["hidden"]);
        remember(elements.status, STATUS_ATTRIBUTES);
        remember(elements.cancel, CANCEL_ATTRIBUTES, ["hidden", "disabled"]);
        return states;
      }
      
      
      function restoreAttachedState(states) {
        for (const [element, state] of states) {
          restoreAttributes(element, state.attributes);
          for (const [property, value] of Object.entries(state.properties)) element[property] = value;
          element.textContent = state.textContent;
        }
      }
      
      
      function setText(element, value) {
        if (!element) return;
        const text = value === null || value === undefined ? "" : String(value);
        if (element.textContent !== text) element.textContent = text;
      }
      
      
      function setStateAttributes(element, values) {
        if (!element) return;
        for (const [name, value] of Object.entries(values)) {
          if (value === null || value === undefined) element.removeAttribute(name);
          else element.setAttribute(name, String(value));
        }
      }
      
      
      function removeElement(element) {
        if (!element) return;
        if (typeof element.remove === "function") element.remove();
        else if (element.parentNode) element.parentNode.removeChild(element);
      }
      
      
      function eventConstructor(host) {
        const view = host.ownerDocument && host.ownerDocument.defaultView;
        if (view && typeof view.CustomEvent === "function") return view.CustomEvent;
        if (typeof CustomEvent === "function") return CustomEvent;
        return null;
      }
      
      
      function dispatchAdapterEvent(host, type, detail) {
        if (!host || typeof host.dispatchEvent !== "function") return true;
        const EventType = eventConstructor(host);
        const event = EventType
          ? new EventType(type, { detail, bubbles: true, composed: true })
          : { type, detail, bubbles: true, composed: true, defaultPrevented: false };
        return host.dispatchEvent(event);
      }
      
      
      function lifecycleText(labels, lifecycle, outcome, promoted) {
        if (outcome === "completed") return labels.completed;
        if (outcome === "failed") return labels.failed;
        if (outcome === "cancelled") return labels.cancelled;
        if (lifecycle === "requested") return labels.requested;
        if (lifecycle === "cancelling") return labels.cancelling;
        if (lifecycle === "cancelled") return labels.cancelled;
        return promoted ? `${labels.promoted}; ${labels.active}` : labels.active;
      }
      
      
      function detailText(view) {
        const main = view.indeterminate
          ? view.countText
          : (view.promotedValueText || view.valueText || view.countText);
        return [main, view.elapsedText, view.rateText, view.etaText].filter(Boolean).join(" | ");
      }
      
      
      class WebThermometer {
        constructor(host, options = {}, attachToken = null, attachedElements = null) {
          this._host = assertElement(host, "host");
          if (INSTANCES.has(this._host)) {
            throw new Error("host already has an active WebThermometer");
          }
          this._options = resolveOptions(options);
          this._attached = attachToken === ATTACH_TOKEN;
          this._elements = this._attached
            ? normalizeAttachedElements(attachedElements, this._options)
            : createCanonicalElements(this._host, this._options);
          this._hostSnapshot = captureAttributes(this._host, HOST_STATE_ATTRIBUTES);
          this._attachedSnapshot = this._attached ? captureAttachedState(this._elements) : null;
          this._destroyed = false;
          this._idle = true;
          this._lastTerminal = false;
          this._cancelSent = false;
          this._lastEnvelope = null;
          this._lastView = null;
          this._boundCancel = (event) => this._handleCancel(event);
          if (this._elements.cancel) this._elements.cancel.addEventListener("click", this._boundCancel);
          INSTANCES.set(this._host, this);
          this._configureSemantics();
          this.reset();
        }
      
        static attach(elements, options = {}) {
          if (!elements || typeof elements !== "object") {
            throw new TypeError("WebThermometer.attach() requires an element map");
          }
          return new WebThermometer(elements.host, options, ATTACH_TOKEN, elements);
        }
      
        get host() {
          return this._host;
        }
      
        get destroyed() {
          return this._destroyed;
        }
      
        _assertLive() {
          if (this._destroyed) throw new Error("WebThermometer has been destroyed");
        }
      
        _configureSemantics() {
          const { label, progress, status } = this._elements;
          progress.setAttribute("max", "100");
          progress.setAttribute("aria-valuemin", "0");
          progress.setAttribute("aria-valuemax", "100");
          if (label) {
            let id = label.getAttribute("id");
            if (!id) {
              labelSequence += 1;
              id = `thermx-progress-label-${labelSequence}`;
              label.setAttribute("id", id);
            }
            progress.setAttribute("aria-labelledby", id);
            progress.removeAttribute("aria-label");
          }
          if (status) {
            status.setAttribute("aria-live", this._options.announce);
            status.setAttribute("aria-atomic", "true");
            if (this._options.announce === "polite") status.setAttribute("role", "status");
            else status.removeAttribute("role");
          }
        }
      
        render(input) {
          this._assertLive();
          const envelope = normalizeProgressInput(input);
          const view = present(envelope, this._options.presentation);
          const state = envelope.state;
          const lifecycle = envelope.cancellation ? envelope.cancellation.state : "active";
          const outcome = envelope.terminal_outcome ?? envelope.terminalOutcome ?? null;
          const terminal = outcome !== null;
          const promoted = state.promoted_from !== null && state.promoted_from !== undefined;
          const label = view.labelText || this._options.labels.progress;
          const detail = detailText(view);
          const stateText = lifecycleText(this._options.labels, lifecycle, outcome, promoted);
          const status = `${label} — ${stateText}`;
      
          if ((this._idle || this._lastTerminal) && !terminal && lifecycle === "active") {
            this._cancelSent = false;
          }
      
          const stateAttributes = {
            "data-thermx-state": terminal ? "terminal" : "running",
            "data-thermx-mode": view.mode,
            "data-thermx-lifecycle": lifecycle,
            "data-thermx-outcome": outcome || "none",
            "data-thermx-promoted": promoted ? "true" : "false",
            "aria-busy": terminal ? "false" : "true",
          };
          setStateAttributes(this._host, stateAttributes);
          setStateAttributes(this._elements.root, stateAttributes);
          setText(this._elements.label, label);
          setText(this._elements.percent, view.percentText ? view.percentText.trim() : this._options.labels.unknown);
          setText(this._elements.detail, detail);
          setText(this._elements.status, status);
          if (this._elements.detail) this._elements.detail.hidden = !this._options.showDetails;
          if (this._elements.percent) this._elements.percent.hidden = false;
      
          const progress = this._elements.progress;
          progress.hidden = false;
          if (view.indeterminate) {
            progress.removeAttribute("value");
            progress.removeAttribute("aria-valuenow");
            progress.setAttribute("aria-valuetext", detail
              ? `${this._options.labels.unknown}; ${detail}`
              : this._options.labels.unknown);
          } else {
            const percent = Math.max(0, Math.min(100, Number(state.percent)));
            progress.setAttribute("value", String(percent));
            progress.setAttribute("aria-valuenow", String(percent));
            progress.setAttribute("aria-valuetext", [view.percentText && view.percentText.trim(), detail]
              .filter(Boolean).join("; "));
          }
          if (!this._elements.label) progress.setAttribute("aria-label", label);
      
          const canCancel = this._options.cancellable
            && !terminal
            && lifecycle === "active"
            && !this._cancelSent;
          if (this._elements.cancel) {
            this._elements.cancel.hidden = !this._options.cancellable;
            this._elements.cancel.disabled = !canCancel;
            this._elements.cancel.setAttribute("aria-disabled", canCancel ? "false" : "true");
            setText(this._elements.cancel, this._options.labels.cancel);
          }
      
          this._idle = false;
          this._lastTerminal = terminal;
          this._lastEnvelope = envelope;
          this._lastView = view;
          return view;
        }
      
        reset() {
          this._assertLive();
          const labels = this._options.labels;
          setStateAttributes(this._host, {
            "data-thermx-state": "idle",
            "data-thermx-mode": null,
            "data-thermx-lifecycle": null,
            "data-thermx-outcome": null,
            "data-thermx-promoted": null,
            "aria-busy": "false",
          });
          setStateAttributes(this._elements.root, {
            "data-thermx-state": "idle",
            "data-thermx-mode": null,
            "data-thermx-lifecycle": null,
            "data-thermx-outcome": null,
            "data-thermx-promoted": null,
            "aria-busy": "false",
          });
          setText(this._elements.label, labels.progress);
          setText(this._elements.percent, "");
          setText(this._elements.detail, "");
          setText(this._elements.status, labels.idle);
          this._elements.progress.hidden = true;
          this._elements.progress.removeAttribute("value");
          this._elements.progress.removeAttribute("aria-valuenow");
          this._elements.progress.setAttribute("aria-valuetext", labels.idle);
          if (!this._elements.label) this._elements.progress.setAttribute("aria-label", labels.progress);
          if (this._elements.percent) this._elements.percent.hidden = true;
          if (this._elements.detail) this._elements.detail.hidden = true;
          if (this._elements.cancel) {
            this._elements.cancel.hidden = true;
            this._elements.cancel.disabled = true;
            this._elements.cancel.setAttribute("aria-disabled", "true");
            setText(this._elements.cancel, labels.cancel);
          }
          this._idle = true;
          this._lastTerminal = false;
          this._cancelSent = false;
          this._lastEnvelope = null;
          this._lastView = null;
        }
      
        destroy() {
          if (this._destroyed) return false;
          if (this._elements.cancel) this._elements.cancel.removeEventListener("click", this._boundCancel);
          if (this._attached) restoreAttachedState(this._attachedSnapshot);
          else removeElement(this._elements.root);
          restoreAttributes(this._host, this._hostSnapshot);
          INSTANCES.delete(this._host);
          this._destroyed = true;
          this._lastEnvelope = null;
          this._lastView = null;
          return true;
        }
      
        _handleCancel(event) {
          if (this._destroyed || this._cancelSent || !this._options.cancellable || !this._lastEnvelope) return;
          const lifecycle = this._lastEnvelope.cancellation ? this._lastEnvelope.cancellation.state : "active";
          const outcome = this._lastEnvelope.terminal_outcome ?? this._lastEnvelope.terminalOutcome ?? null;
          if (lifecycle !== "active" || outcome !== null) return;
      
          this._cancelSent = true;
          if (this._elements.cancel) {
            this._elements.cancel.disabled = true;
            this._elements.cancel.setAttribute("aria-disabled", "true");
          }
          const detail = Object.freeze({ thermometer: this, view: this._lastView, originalEvent: event || null });
          dispatchAdapterEvent(this._host, "thermxcancel", detail);
          if (!this._options.onCancel) return;
      
          let result;
          try {
            result = this._options.onCancel(detail);
          } catch (error) {
            this._reportError(error, "cancel");
            return;
          }
          if (result && typeof result.then === "function") {
            Promise.resolve(result).catch((error) => this._reportError(error, "cancel"));
          }
        }
      
        _reportError(error, source) {
          if (this._destroyed) return;
          const envelope = this._lastEnvelope;
          const lifecycle = envelope && envelope.cancellation ? envelope.cancellation.state : "active";
          const outcome = envelope ? (envelope.terminal_outcome ?? envelope.terminalOutcome ?? null) : null;
          if (envelope && lifecycle === "active" && outcome === null) {
            this._cancelSent = false;
            if (this._elements.cancel) {
              this._elements.cancel.disabled = false;
              this._elements.cancel.setAttribute("aria-disabled", "false");
            }
          }
          const detail = Object.freeze({ error, source, thermometer: this });
          if (this._options.onError) {
            try { this._options.onError(detail); } catch { /* application callback owns its failure */ }
          }
          dispatchAdapterEvent(this._host, "thermxerror", detail);
        }
      }
      
      
      function createWebThermometer(host, options = {}) {
        return new WebThermometer(host, options);
      }
      
      
      module.exports = {
        WEB_LABEL_DEFAULTS,
        WebThermometer,
        createWebThermometer,
        create_web_thermometer: createWebThermometer,
        normalizeProgressInput,
        normalize_progress_input: normalizeProgressInput,
      };
    };
    const cache = Object.create(null);
    function requireModule(id) {
      if (cache[id]) return cache[id].exports;
      const factory = modules[id];
      if (!factory) throw new Error(`NodeThermX Web module not found: ${id}`);
      const module = { exports: {} };
      cache[id] = module;
      factory(module, module.exports, requireModule);
      return module.exports;
    }
    return requireModule("./web_thermometer");
  }());
  global.NodeThermXWeb = api;
}(typeof globalThis !== "undefined" ? globalThis : self));
