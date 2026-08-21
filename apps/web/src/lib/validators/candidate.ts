import { z } from "zod";

export const candidateSchema = z.object({
  name: z.string().trim().min(1, "Please enter your name"),
  target_roles: z.array(z.string()).min(1, "Choose at least one role"),
  skills: z.array(z.string()).default([]),
  years_of_experience: z.coerce.number().min(0).max(60),
  seniority: z.string().nullable(),
  preferred_countries: z.array(z.string()).default([]),
  visa_required: z.boolean(),
  relocation_preference: z.string(),
  remote_preference: z.string(),
  excluded_locations: z.array(z.string()).default([]),
});

export type CandidateFormValues = z.infer<typeof candidateSchema>;
