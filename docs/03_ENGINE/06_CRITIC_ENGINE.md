# Document Metadata

**Document:** 06_CRITIC_ENGINE.md
**Version:** 1.0.0
**Status:** Draft
**Owner:** AIVE Core Team

Depends On:
- [None]

Used By:
- [None]

---
# Purpose

The Critic Engine is the adversarial intelligence layer of AIVE.

Its responsibility is to systematically challenge every discovery before it is accepted.

Unlike the Discovery Engine, which attempts to generate opportunities, the Critic Engine attempts to reject them.

Healthy disagreement produces stronger discoveries.

---

# Philosophy

Every discovery should survive criticism.

If a discovery cannot defend itself,

it should never reach the user.

The Critic Engine therefore behaves as an internal skeptic rather than an assistant.

---

# Responsibilities

Challenge assumptions.

Identify logical weaknesses.

Find contradictory evidence.

Estimate implementation risk.

Identify missing evidence.

Detect reasoning flaws.

Reject weak discoveries.

Recommend improvements.

---

# Non-Responsibilities

Generate discoveries.

Search for novelty.

Produce reports.

Modify knowledge.

---

# Inputs

Discovery Objects

Opportunity Objects

Reasoning Objects

Evidence Graph

Validation Results

Novelty Reports

---

# Outputs

Criticism Report

Weakness Analysis

Risk Assessment

Suggested Improvements

Acceptance Recommendation

Rejection Recommendation

---

# Internal Modules

Logic Critic

Evidence Critic

Market Critic

Technical Critic

Scientific Critic

Commercial Critic

Ethical Critic

Regulatory Critic

---

# Criticism Pipeline

Discovery

↓

Assumption Analysis

↓

Evidence Review

↓

Contradiction Search

↓

Risk Analysis

↓

Weakness Detection

↓

Recommendation

↓

Validation Engine

---

# Criticism Questions

Is the evidence sufficient?

What assumptions remain untested?

Does contradictory evidence exist?

Could this already exist?

Is implementation realistic?

Who benefits?

Who disagrees?

What would invalidate this discovery?

---

# Failure Modes

Overly aggressive rejection.

False acceptance.

Missing contradictions.

Hallucinated criticism.

Incomplete evidence review.

---

# Interfaces

Consumes:

Novelty Engine

Reasoning Engine

Produces:

Validation Engine

Learning Engine

Discovery Feedback

---

# Metrics

False Positive Rate

False Negative Rate

Evidence Coverage

Criticism Accuracy

Expert Agreement

---

# Future

Future versions should support domain-specific critic panels composed of multiple specialized AI experts.
