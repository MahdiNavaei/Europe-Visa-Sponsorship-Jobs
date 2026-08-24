# Production sponsor evidence

`sponsors.csv.gz` is generated, not hand-maintained. `sponsors.manifest.json`
records generation time, row counts, the dataset SHA-256, and official-source
provenance. New automated refreshes also retain SHA-256 hashes of both downloaded
inputs. The dataset contains only the fields
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
  --output data/sponsors.csv.gz
```

Validate the checked-in cache and its freshness without network access:

```powershell
python scripts/build_sponsor_registry.py --validate `
  --output data/sponsors.csv.gz `
  --manifest data/sponsors.manifest.json `
  --max-age-days 45
```

The scheduled refresh workflow downloads both sources itself, enforces minimum
record counts, records input hashes, and opens or updates a reviewable pull
request when the official registers change. It never substitutes guessed or
third-party company data.

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
