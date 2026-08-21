# Product Definition

## Problem

Many international applicants spend hours applying to jobs that are impossible because of hidden immigration restrictions.

A company may:

- have offices in Europe
- advertise internationally
- even have sponsored employees

but the specific job may still require existing work authorization.

## Product Goal

Return only opportunities with a high probability of being realistic for non-EU candidates.

## Job Eligibility Pipeline

Every job should pass through:

1. Active job validation
2. Role classification
3. Sponsorship evidence collection
4. Restriction detection
5. Country immigration rule validation
6. Candidate matching

## Evidence Model

A job should never simply be marked:

```
visa_sponsorship=true
```

Instead store evidence:

```
Company evidence:
- recognised sponsor registry
- previous relocation history
- international hiring history

Job evidence:
- sponsorship mentioned
- relocation mentioned
- international applicants accepted

Negative evidence:
- EU only
- must already have right to work
- local candidates only
```

## Confidence Score

Example:

```
Visa Compatibility: 91%

Positive:
✓ Recognised sponsor
✓ Relocation support mentioned
✓ English workplace
✓ No EU-only restriction

Unknown:
? No direct Iranian employee evidence
```

The system should explain decisions instead of producing black-box rankings.
