# Document Metadata

**Document:** 04_CLAIM_MODEL.md
**Version:** 1.0.0
**Status:** Draft

Depends On:
- [None]

Used By:
- [None]

---
# Purpose

Claims are the primary reasoning units inside AIVE.

Rather than reasoning over entire papers, AIVE reasons over individual claims.

---

# Why Claims?

Scientific papers contain:

Background

Methods

Discussion

References

Future Work

Only some sentences represent scientific claims.

Those claims become independent Knowledge Objects.

---

# Definition

A Claim is a structured statement that can be supported, contradicted or refined by evidence.

Claims should always remain verifiable.

---

# Examples

"The catalyst increases efficiency by 18%."

"Protein X suppresses Pathway Y."

"Battery degradation accelerates above 45°C."

Each becomes its own Claim Object.

---

# Components

Every Claim contains:

Claim ID

Statement

Evidence

Author

Source

Confidence

Supporting Objects

Contradicting Objects

Version

History

Discovery Links

Validation Status

---

# Claim Relationships

supports

contradicts

extends

refines

supersedes

explains

requires

depends_on

equivalent_to

---

# Claim Confidence

Confidence emerges from

Evidence Quality

Independent Confirmation

Experimental Support

Contradictions

Expert Review

Temporal Stability

---

# Claim Evolution

Claims never disappear.

They evolve.

Old claims remain historically accessible.

New evidence updates confidence.

---

# Why Claim-Level Reasoning?

Instead of

Paper A

↓

Paper B

↓

Paper C

AIVE reasons

Claim

↓

Evidence

↓

Mechanism

↓

Contradiction

↓

Discovery

This dramatically improves explainability.

---

# Goal

Claims become the primary semantic building blocks used by every reasoning agent inside AIVE.
