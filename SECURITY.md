# Security policy

## Supported releases

Security fixes are applied to the current maintained release line. Users should update to the newest published Career Radar release before reporting an issue that has already been fixed upstream.

## Reporting a vulnerability

Please avoid publishing exploitable details in a public issue before the maintainer has had a reasonable opportunity to investigate.

Preferred reporting path:

1. Use GitHub's private vulnerability reporting / repository Security tab when it is available for this repository.
2. If private vulnerability reporting is unavailable, open a minimal public issue asking for a private security contact without including exploit details, secrets, personal data, or a working proof of exploitation.

A useful report includes the affected version or commit, operating system/runtime, expected security boundary, observed behavior, reproducible steps, and the smallest safe evidence needed to confirm the issue.

## Scope

Security-sensitive areas include:

- Windows release provenance and Authenticode signing,
- catalog and sponsor-data integrity verification,
- SSRF/network boundary enforcement,
- candidate profile authorization and local-data isolation,
- dependency/supply-chain integrity,
- GitHub Actions release and market-data workflows.

Please do not perform destructive testing against third-party employer or ATS infrastructure. Career Radar consumes public job-data interfaces; authorization to test Career Radar does not grant authorization to test those external services.

## Release signing

Official tagged Windows releases follow [`CODE_SIGNING_POLICY.md`](CODE_SIGNING_POLICY.md). Suspected signing-policy violations, release tampering, or mismatched published checksums should be treated as security issues.
