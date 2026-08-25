# Privacy policy

Career Radar is designed as a local-first desktop application. This policy describes the official Windows desktop build published from this repository.

## Data stored locally

The desktop application stores its runtime database and user state under the user's local application-data directory. This can include:

- candidate profile fields and preferences,
- selected roles, skills and country preferences,
- saved jobs,
- application tracking state,
- user-entered notes,
- cached market/catalog data and refresh status.

This data is not uploaded to a Career Radar-operated account, analytics service or telemetry backend.

## Network activity

Career Radar needs network access to provide current job data. The desktop application may make outbound requests to:

- the project's published GitHub market-data/catalog resources,
- public employer/ATS endpoints used to retrieve current vacancies when a local recovery refresh is required,
- official/public sponsor-evidence sources during repository maintenance workflows, not from a normal installed client,
- an external job/application URL when the user chooses to open that destination.

Candidate profile data, saved-job state, application tracking state and notes are not included in these market-data requests.

## Analytics and telemetry

The official desktop build does not send product analytics, advertising identifiers or behavioral telemetry to the project maintainer.

The local API exposes operational health/metrics to the local runtime for diagnostics. These metrics are not automatically transmitted to a remote Career Radar service.

## Third-party services

Public job data and application links are supplied by third-party employers and ATS providers. Opening a third-party site is governed by that site's own privacy policy and terms.

GitHub is used to publish project releases and the market-data catalog. GitHub's own privacy terms apply to requests made to GitHub infrastructure.

## Hosted/self-managed deployments

The repository can also be deployed by third parties using PostgreSQL and the web/API stack. Operators of those deployments are responsible for their own privacy policy, access controls, retention and infrastructure. This document does not claim that an independently operated deployment has the same data-handling boundary as the official local desktop build.

## Changes

Material changes to desktop data handling will be documented in this file and reviewed as part of the release process.
