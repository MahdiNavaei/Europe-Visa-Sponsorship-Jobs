type Translator = (key: string, values?: Record<string, string>) => string;

function valueAfterPrefix(value: string, prefix: string): string | null {
  return value.startsWith(prefix) ? value.slice(prefix.length).replace(/\.$/, "") : null;
}

/** Localize deterministic matcher explanations without translating source evidence. */
export function localizeRecommendationReason(value: string, locale: string, t: Translator): string {
  if (locale !== "fa") return value;

  const dynamicRules: Array<[string, string]> = [
    ["The job is in preferred country ", "preferredCountry"],
    ["The job country ", "nonPreferredCountry"],
    ["Matched required skills: ", "matchedRequiredSkills"],
    ["Missing required skills: ", "missingRequiredSkills"],
  ];
  for (const [prefix, key] of dynamicRules) {
    const dynamicValue = valueAfterPrefix(value, prefix);
    if (dynamicValue !== null) {
      const countryValue = key === "nonPreferredCountry" ? dynamicValue.replace(/ is not in the preferred countries$/, "") : dynamicValue;
      return t(key, { value: countryValue, country: countryValue, skills: dynamicValue });
    }
  }

  const exact: Record<string, string> = {
    "The remote role is explicitly limited to Europe/EEA markets.": "europeRemote",
    "Remote work matches the candidate preference.": "remoteMatches",
    "The job passed the strict sponsorship eligibility gate.": "sponsorshipPassed",
    "The candidate does not require sponsorship.": "sponsorshipNotRequired",
    "The job location is excluded by the candidate.": "excludedLocation",
    "The remote role is restricted to the United States/North America.": "northAmericaOnly",
    "The candidate requires remote work.": "remoteRequired",
    "Relocation is required but this country is not preferred.": "relocationCountryMismatch",
    "Sponsorship evidence is incomplete for a candidate who needs a visa.": "sponsorshipIncomplete",
    "The job failed the sponsorship eligibility gate.": "sponsorshipFailed",
    "The vacancy contains a work-authorization restriction.": "workAuthorizationRestriction",
    "The vacancy did not publish enough skill requirements to assess skill fit.": "skillsUnavailable",
    "The role aligns with the candidate's target role family.": "roleMatches",
    "The role is outside the candidate's target role family.": "roleMismatch",
    "The role seniority matches the candidate profile.": "seniorityMatches",
    "The role seniority differs from the candidate profile.": "seniorityMismatch",
    "The vacancy did not publish enough experience requirements to assess experience fit.": "experienceUnavailable",
    "Recognized sponsor evidence is on file.": "sponsorRegistry",
    "Relocation support is mentioned.": "relocationMentioned",
    "The employer says relocation is provided.": "relocationProvided",
    "International candidates are welcomed.": "internationalCandidates",
    "Applications from abroad are accepted.": "abroadApplications",
    "The vacancy explicitly mentions visa sponsorship.": "visaMentioned",
    "The employer explicitly mentions sponsoring a work visa.": "workVisaMentioned",
    "Work-permit support is mentioned.": "workPermitMentioned",
    "Immigration support is mentioned.": "immigrationMentioned",
    "The vacancy says sponsorship is unavailable.": "sponsorshipUnavailable",
    "Existing work authorization without sponsorship is required.": "existingAuthorization",
    "Existing local work rights are required.": "localWorkRights",
    "The vacancy is restricted to EU/EEA candidates.": "euEeaOnly",
    "The vacancy is limited to local or regional residents.": "localResidentsOnly",
    "The vacancy requires a specific citizenship.": "citizenshipRequired",
  };
  return exact[value] ? t(exact[value]) : t("unavailableReason");
}
