# Product Definition

## Problem

A large job board is not useful to a candidate who needs immigration support if most vacancies silently require existing work authorization.

The product therefore optimizes for **actionable opportunities**, not raw job count.

## Product goal

Return European technical vacancies where a non-EU candidate has strong evidence that employer-supported immigration is realistically possible.

The current system does not require a job to explicitly mention Iran. It does require the absence of detected nationality/residency restrictions and strong sponsorship evidence.

## Core product rules

1. Prefer first-party company ATS/career data over aggregators.
2. Never infer that every vacancy is sponsored just because the company has sponsored before.
3. Hard negative restrictions override positive keywords.
4. Missing evidence becomes `unknown`, not `eligible`.
5. Default API results contain only `eligible` jobs.
6. Every decision must be explainable with stored evidence.
7. No paid LLM/API is required in the current architecture.

## Eligibility pipeline

```text
active public vacancy
        ↓
supported technical role
        ↓
country rule available
        ↓
hard restriction detection
        ↓
job-level sponsorship evidence
        +
verified company sponsor evidence when required
        ↓
strict eligibility decision
```

## Evidence model

### Positive job evidence

Examples:

- visa sponsorship
- work permit support
- immigration support
- Highly Skilled Migrant / kennismigrant
- EU Blue Card
- visa + relocation support

### Supporting evidence

- relocation package/support
- international candidates welcome
- applications from abroad

### Company evidence

- verified official sponsor register entry
- future country-specific verified datasets

### Hard negative evidence

Examples:

- no visa sponsorship
- unable to sponsor
- must already have right to work
- authorized to work without sponsorship
- EU/EEA candidates only
- specified citizenship required
- candidate must already reside in a restricted region

## Strictness

The system is deliberately conservative. A false-positive recommendation wastes the user's time and damages trust. Unknown opportunities remain queryable for debugging/research, but are hidden from the default user-facing result set.
