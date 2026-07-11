# Document Metadata

**Document:** 12_AGENT_OUTPUT_PROTOCOL.md
**Version:** 1.0.0
**Status:** Draft

Depends On:
- [None]

Used By:
- [None]

---
# Purpose

Agents should never return arbitrary text.

Every agent produces structured outputs that can be consumed by downstream engines and agents.

This protocol standardizes those outputs.

---

# Philosophy

Structure before language.

Language explains.

Objects execute.

---

# Output Types

Knowledge Object

Evidence Object

Reasoning Object

Discovery Object

Opportunity Object

Validation Report

Critic Report

Learning Event

System Event

Tool Result

---

# Output Metadata

Object ID

Agent ID

Timestamp

Version

Confidence

Evidence References

Reasoning References

Validation Status

Correlation ID

---

# Validation Rules

Every output must be:

Schema Valid

Versioned

Traceable

Evidence Linked

Machine Readable

---

# Failure Outputs

Timeout

Insufficient Evidence

Tool Failure

Low Confidence

Needs Human Review

Retry Requested

---

# Goal

Every output produced by AIVE should become reusable structured knowledge rather than disposable text.
