# Europe Visa Sponsorship Jobs

> Find European tech jobs where relocation and visa sponsorship are realistically possible for non-EU candidates.

## Vision

Europe-Visa-Sponsorship-Jobs is an open-source job intelligence platform focused on helping international candidates discover software engineering, data, and AI roles in Europe.

The goal is not to collect more jobs. The goal is to remove jobs that waste applicants' time.

## Core Principles

- Evidence-based visa eligibility
- Prefer company career pages and ATS sources over job aggregators
- Detect hidden restrictions (`EU only`, `must already have work authorization`, etc.)
- Explain why a job is recommended
- Support community contributions for countries, companies, and immigration rules

## Initial Scope

Countries:

- Netherlands
- Germany
- United Kingdom
- Ireland
- Sweden
- Finland
- Denmark

Job families:

- Software Engineering
- Backend
- Frontend
- Full Stack
- Data Engineering
- Data Science
- Machine Learning Engineering
- AI Engineering
- MLOps
- DevOps / Cloud

## Architecture

```
Sources
  |
  +-- ATS Connectors
  |     +-- Greenhouse
  |     +-- Lever
  |     +-- Ashby
  |     +-- Workable
  |
  +-- Job Boards
        +-- Relocation focused sources

          |
          v

Job Normalization Layer

          |
          v

Eligibility Engine
  |
  +-- Sponsorship signals
  +-- Immigration rules
  +-- Restriction detection
  +-- Company history

          |
          v

Matching Engine
  |
  +-- Skills
  +-- Experience
  +-- Role similarity

          |
          v

API + Dashboard
```

## Status

🚧 Early development

## License

MIT
