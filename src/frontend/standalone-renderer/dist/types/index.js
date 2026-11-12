"use strict";
// ── Component Definitions (templates) ──────────────────
Object.defineProperty(exports, "__esModule", { value: true });
exports.PROJECT_SCHEMA_VERSION = void 0;
// ── Project (top-level, serializable to JSON) ──────────
// Schema version written by exportProject. Anything older reaching the
// editor (an imported file, a stored draft) goes through the backend's
// /projects/migrate/ first; the frontend itself carries no migration logic.
exports.PROJECT_SCHEMA_VERSION = 4;
