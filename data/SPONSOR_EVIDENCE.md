# Production sponsor evidence

`sponsors.csv` is generated, not hand-maintained. It contains only the fields
needed for strict company-name matching:

- company name;
- country;
- official register name; and
- source page URL.

The 2026-08-23 artifact was generated with:

```powershell
python scripts/build_sponsor_registry.py `
  --uk-csv build/ukvi-workers.csv `
  --ind-html build/ind-work-register.html `
  --output data/sponsors.csv
```

The inputs are current downloads from the official [UKVI worker sponsor
register](https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers)
and the [IND work recognised-sponsor
register](https://ind.nl/en/public-register-recognised-sponsors/public-register-work).
The UK source is published under the [Open Government Licence
v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
The IND register remains attributed to the IND and is used only as factual
public-register evidence; refreshes must retain its source URL and comply with
the source site's current terms.

Registry membership is not proof that a particular vacancy sponsors an
applicant. Career Radar retains the official source link and still requires
job-level evidence; explicit work-authorisation or no-sponsorship wording
always overrides a registry match.
