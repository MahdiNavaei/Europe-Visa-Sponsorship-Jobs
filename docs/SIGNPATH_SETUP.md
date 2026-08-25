# SignPath Foundation setup for Career Radar

Career Radar uses SignPath Foundation for official tagged Windows releases. The repository is already prepared for SignPath GitHub origin verification; this page records the one-time external provisioning that cannot be stored in source control.

## Repository-side configuration

The release workflow defaults to these SignPath slugs:

- project: `career-radar`
- signing policy: `release-signing`
- launcher artifact configuration: `launcher`
- installer artifact configuration: `installer`

The matching artifact-configuration sources are version controlled at:

- `.signpath/artifact-configurations/launcher.xml`
- `.signpath/artifact-configurations/installer.xml`

If SignPath provisions different slugs, set these optional GitHub repository variables instead of editing the workflow:

- `SIGNPATH_PROJECT_SLUG`
- `SIGNPATH_SIGNING_POLICY_SLUG`
- `SIGNPATH_LAUNCHER_ARTIFACT_CONFIGURATION_SLUG`
- `SIGNPATH_INSTALLER_ARTIFACT_CONFIGURATION_SLUG`

## One-time SignPath Foundation provisioning

1. Apply for the free Open Source subscription at https://signpath.org/apply.html using this repository as the project source.
2. Point the application/review to `CODE_SIGNING_POLICY.md`, `PRIVACY.md`, the MIT `LICENSE`, and the existing public GitHub Releases history.
3. Install/authorize the SignPath GitHub App for `MahdiNavaei/Europe-Visa-Sponsorship-Jobs` when SignPath asks for trusted-build-system access.
4. Create/import the two artifact configurations from `.signpath/artifact-configurations/`.
5. Configure the release signing policy and its required manual approver according to the Foundation policy.
6. Create a SignPath CI/API token that can submit signing requests for this project.

SignPath Foundation requires manual approval of release signing requests. The GitHub Actions job waits for that approval and fails rather than publishing an unsigned tagged release.

## GitHub settings after SignPath approval

Add exactly these mandatory values to the GitHub repository:

- Actions secret: `SIGNPATH_API_TOKEN`
- Actions repository variable: `SIGNPATH_ORGANIZATION_ID`

Do not commit either value to the repository.

The workflow uses GitHub's built-in `GITHUB_TOKEN` only to let SignPath verify the GitHub Actions build origin and retrieve the uploaded unsigned artifact.

## What the tagged workflow does

For a `v*` release tag, `.github/workflows/windows-package.yml`:

1. validates release inputs and package version/tag consistency;
2. builds `CareerRadar.exe` with explicit `Career Radar` product/version metadata;
3. uploads the unsigned launcher to GitHub Actions;
4. submits that GitHub artifact ID to SignPath and waits for approval/completion;
5. verifies the returned launcher's Authenticode signature;
6. builds the portable package and Windows installer using the signed launcher;
7. uploads the unsigned installer and submits it to SignPath;
8. verifies the returned installer's Authenticode signature;
9. generates SHA-256 checksums only after signing;
10. runs clean installed/portable smoke tests and the two-cycle market-data test;
11. publishes the GitHub Release only if the build job succeeds.

Pull-request and normal `main` builds intentionally skip SignPath and remain test-only artifacts.

## Final v1.1.4 release sequence

After SignPath is provisioned and the GitHub secret/variable are configured:

1. ensure the final release commit is on `main` and all normal CI is green;
2. create `v1.1.4` on that exact commit;
3. approve the two SignPath release-signing requests when they appear;
4. wait for the Windows workflow and GitHub Release publication to finish;
5. download the published setup/portable/checksum files again and verify SHA-256 and Authenticode;
6. record the final evidence and freeze v1.1.4.

The release must remain blocked if SignPath signing cannot be completed.
