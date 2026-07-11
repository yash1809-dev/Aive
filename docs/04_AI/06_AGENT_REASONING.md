# Document Metadata

**Document:** 06_AGENT_REASONING.md
**Version:** 1.0.0
**Status:** Draft

Depends On:
- [None]

Used By:
- [None]

---
# Purpose

This document defines how agents execute reasoning tasks assigned by the Engine Layer.

Agents do not invent reasoning strategies.

They execute them.

---

# Philosophy

Thinking belongs to the Engine.

Execution belongs to Agents.

This separation keeps cognition independent of implementation.

---

# Agent Responsibilities

Interpret assigned task.

Retrieve required knowledge.

Apply reasoning strategy.

Generate structured outputs.

Return reasoning artifacts.

---

# Supported Reasoning

Deductive

Inductive

Abductive

Analogical

Temporal

Cross-Domain

Constraint-Based

Simulation-Assisted

---

# Reasoning Workflow

Task Assignment

↓

Knowledge Retrieval

↓

Reasoning Execution

↓

Evidence Verification

↓

Output Construction

↓

Return Result

---

# Explainability

Every reasoning result should include

Evidence References

Knowledge References

Reasoning Strategy

Confidence

Assumptions

Uncertainty

---

# Goal

Agent reasoning should remain deterministic, explainable and reusable.
