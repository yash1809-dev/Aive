# Document Metadata

**Document:** 14_DISCOVERY_STATE_MACHINE.md
**Version:** 1.0.0
**Status:** Draft

Depends On:
- [None]

Used By:
- [None]

---
# Purpose

This document defines the finite-state machine governing every Discovery Object.

A Discovery Object always exists in exactly one state.

Transitions occur only through evidence-backed events.

---

# States

Draft

↓

Candidate

↓

Reasoning

↓

Novelty Verification

↓

Criticism

↓

Validation

↓

Accepted

↓

Implemented

↓

Observed

↓

Learning

↓

Historical

↓

Archived

---

# Transition Rules

Every transition requires:

Evidence

Reason

Timestamp

Responsible Engine

Version

No transition may bypass required validation stages.

---

# Invalid Transitions

Draft → Accepted

Candidate → Historical

Reasoning → Archived

These transitions are prohibited.

---

# Benefits

Predictable behavior.

Complete auditability.

Engine interoperability.

Simplified implementation.

Robust lifecycle management.

---

# Goal

Every discovery should evolve through a deterministic, explainable and auditable state machine.
