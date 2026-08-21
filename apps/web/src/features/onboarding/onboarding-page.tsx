"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, ArrowRight, Check, LoaderCircle, MapPin, Plus, Sparkles } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { useCandidate, useCreateCandidate, useUpdateCandidate } from "@/lib/api/hooks";
import { candidateSchema, type CandidateFormValues } from "@/lib/validators/candidate";
import { cn } from "@/lib/utils/cn";
import { formatCountry } from "@/lib/utils/format";
import { setCandidateId, useCandidateId } from "@/lib/utils/candidate";

const roles = ["AI / Machine Learning", "Backend Engineering", "Frontend Engineering", "Data Science", "Data Engineering", "DevOps / Cloud"];
const skills = ["Python", "TypeScript", "SQL", "PyTorch", "Machine Learning", "Docker", "Kubernetes", "AWS", "React", "FastAPI"];
const countries = ["Germany", "Netherlands", "Sweden", "Denmark", "Finland", "Ireland", "United Kingdom"];
const steps = ["role", "skills", "experience", "countries", "visa", "remote"] as const;
const roleLabelsFa: Record<string, string> = {
  "AI / Machine Learning": "هوش مصنوعی / یادگیری ماشین",
  "Backend Engineering": "مهندسی بک‌اند",
  "Frontend Engineering": "مهندسی فرانت‌اند",
  "Data Science": "علم داده",
  "Data Engineering": "مهندسی داده",
  "DevOps / Cloud": "DevOps / کلاد",
};

const defaultValues: CandidateFormValues = {
  name: "",
  target_roles: [],
  skills: [],
  years_of_experience: 3,
  seniority: "mid",
  preferred_countries: [],
  visa_required: true,
  relocation_preference: "preferred",
  remote_preference: "no_preference",
  excluded_locations: [],
};

export function OnboardingPage() {
  const locale = useLocale();
  const t = useTranslations("onboarding");
  const router = useRouter();
  const candidateId = useCandidateId();
  const { data: existingCandidate } = useCandidate(candidateId);
  const isEditing = candidateId !== null && existingCandidate?.id === candidateId;
  const [step, setStep] = useState(0);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const createMutation = useCreateCandidate();
  const updateMutation = useUpdateCandidate();
  const mutationPending = createMutation.isPending || updateMutation.isPending;
  const mutationError = createMutation.error ?? updateMutation.error;
  const { register, handleSubmit, watch, getValues, setValue, trigger, reset, formState: { errors } } = useForm<CandidateFormValues>({ resolver: zodResolver(candidateSchema), defaultValues });
  useEffect(() => {
    if (!isEditing || !existingCandidate) return;
    const values: CandidateFormValues = {
      name: existingCandidate.name,
      target_roles: existingCandidate.target_roles,
      skills: existingCandidate.skills,
      years_of_experience: existingCandidate.years_of_experience,
      seniority: existingCandidate.seniority,
      preferred_countries: existingCandidate.preferred_countries,
      visa_required: existingCandidate.visa_required,
      relocation_preference: existingCandidate.relocation_preference,
      remote_preference: existingCandidate.remote_preference,
      excluded_locations: existingCandidate.excluded_locations,
    };
    reset(values);
    setSelectedRoles(values.target_roles);
    setSelectedSkills(values.skills);
    setSelectedCountries(values.preferred_countries);
  }, [existingCandidate, isEditing, reset]);
  const roleDisplay = useMemo(() => (value: string) => locale === "fa" ? roleLabelsFa[value] ?? value : value, [locale]);
  const toggle = (field: "target_roles" | "skills" | "preferred_countries", value: string) => {
    const current = field === "target_roles" ? selectedRoles : field === "skills" ? selectedSkills : selectedCountries;
    const next = current.includes(value) ? current.filter((item) => item !== value) : [...current, value];
    if (field === "target_roles") setSelectedRoles(next);
    else if (field === "skills") setSelectedSkills(next);
    else setSelectedCountries(next);
    setValue(field, next, { shouldValidate: true });
  };
  const submit = async (values: CandidateFormValues) => {
    const candidate = candidateId
      ? await updateMutation.mutateAsync({ id: candidateId, input: values })
      : await createMutation.mutateAsync(values);
    setCandidateId(candidate.id);
    router.push(`/${locale}/dashboard`);
  };
  const next = () => {
    const fields = step === 0 ? ["name", "target_roles"] : step === 1 ? ["skills"] : step === 3 ? ["preferred_countries"] : [];
    const current = getValues();
    const valid = fields.length === 0 || (step === 0 && current.name.trim().length > 0 && selectedRoles.length > 0) || (step === 1 && selectedSkills.length > 0) || (step === 3 && selectedCountries.length > 0);
    if (valid) setStep((currentStep) => Math.min(currentStep + 1, steps.length - 1));
    else void trigger(fields as (keyof CandidateFormValues)[]);
  };
  const BackIcon = locale === "fa" ? ArrowRight : ArrowLeft;
  const NextIcon = locale === "fa" ? ArrowLeft : ArrowRight;
  return <div className="min-h-[calc(100vh-72px)] px-5 py-10 sm:px-8 lg:px-10 lg:py-16"><div className="mx-auto max-w-4xl"><Link href={`/${locale}`} className="focus-ring inline-flex items-center gap-2 text-sm font-bold text-[var(--muted)] hover:text-[var(--accent)]"><BackIcon size={15} />{t("back")}</Link><div className="mt-8 grid gap-8 lg:grid-cols-[.7fr_1.3fr]"><aside className="rounded-3xl bg-[var(--ink)] p-7 text-[var(--paper)] sm:p-9"><div className="grid size-11 place-items-center rounded-2xl bg-white/10 text-[var(--accent)]"><Sparkles size={20} /></div><p className="mt-8 text-xs font-bold uppercase tracking-[.15em] text-white/50">{t("profileLabel")}</p><h1 className="mt-4 text-3xl font-black leading-tight tracking-[-.05em]">{t("title")}</h1><p className="mt-4 text-sm leading-7 text-white/60">{isEditing ? t("editing") : t("subtitle")}</p><div className="mt-10 space-y-3">{steps.map((item, index) => <div key={item} className={cn("flex items-center gap-3 text-sm", index === step ? "font-bold text-white" : index < step ? "text-[var(--mint)]" : "text-white/35")}><span className={cn("grid size-7 place-items-center rounded-full border text-xs", index < step ? "border-[var(--mint)] bg-[var(--mint)] text-[var(--ink)]" : index === step ? "border-[var(--accent)] bg-[var(--accent)] text-white" : "border-white/20")}>{index < step ? <Check size={13} /> : index + 1}</span>{t(item)}</div>)}</div></aside><Card className="p-6 sm:p-9"><form onSubmit={handleSubmit(submit)}><div className="min-h-[390px]">{step === 0 && <StepBlock eyebrow={t("stepLabel")} title={t("role")}><label className="mb-6 block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">{t("name")}</span><Input {...register("name")} placeholder={t("placeholder")} autoFocus />{errors.name && <ErrorText text={errors.name.message} />}</label><div className="grid gap-3 sm:grid-cols-2">{roles.map((role) => <Choice key={role} selected={selectedRoles.includes(role)} onClick={() => toggle("target_roles", role)}>{roleDisplay(role)}</Choice>)}</div>{errors.target_roles && <ErrorText text={errors.target_roles.message} />}</StepBlock>}{step === 1 && <StepBlock eyebrow={t("stepLabel")} title={t("skills")}><p className="mb-5 text-sm text-[var(--muted)]">{t("skillsHelp")}</p><div className="flex flex-wrap gap-2">{skills.map((skill) => <Choice key={skill} compact selected={selectedSkills.includes(skill)} onClick={() => toggle("skills", skill)}>{skill}</Choice>)}</div></StepBlock>}{step === 2 && <StepBlock eyebrow={t("stepLabel")} title={t("experience")}><div className="grid gap-3 sm:grid-cols-2"><Choice selected={watch("seniority") === "junior"} onClick={() => setValue("seniority", "junior")}>{t("early")}</Choice><Choice selected={watch("seniority") === "mid"} onClick={() => setValue("seniority", "mid")}>{t("mid")}</Choice><Choice selected={watch("seniority") === "senior"} onClick={() => setValue("seniority", "senior")}>{t("senior")}</Choice><Choice selected={watch("seniority") === "staff"} onClick={() => setValue("seniority", "staff")}>{t("staff")}</Choice></div><label className="mt-8 block"><span className="mb-2 block text-xs font-bold text-[var(--muted)]">{t("years")}</span><Input type="number" min="0" max="60" step="0.5" {...register("years_of_experience", { valueAsNumber: true })} /></label></StepBlock>}{step === 3 && <StepBlock eyebrow={t("stepLabel")} title={t("countries")}><p className="mb-5 text-sm text-[var(--muted)]">{t("countriesHelp")}</p><div className="grid gap-3 sm:grid-cols-2">{countries.map((country) => <Choice key={country} selected={selectedCountries.includes(country)} onClick={() => toggle("preferred_countries", country)}><MapPin size={15} />{formatCountry(country, locale)}</Choice>)}</div></StepBlock>}{step === 4 && <StepBlock eyebrow={t("stepLabel")} title={t("visa")}><div className="space-y-3"><Choice selected={watch("visa_required") === true} onClick={() => setValue("visa_required", true)}>{t("visaYes")}</Choice><Choice selected={watch("visa_required") === false} onClick={() => setValue("visa_required", false)}>{t("visaNo")}</Choice></div></StepBlock>}{step === 5 && <StepBlock eyebrow={t("stepLabel")} title={t("remote")}><div className="space-y-3"><Choice selected={watch("remote_preference") === "preferred"} onClick={() => setValue("remote_preference", "preferred")}>{t("remotePreferred")}</Choice><Choice selected={watch("remote_preference") === "no_preference"} onClick={() => setValue("remote_preference", "no_preference")}>{t("remoteOpen")}</Choice><Choice selected={watch("remote_preference") === "required"} onClick={() => setValue("remote_preference", "required")}>{t("remoteRequired")}</Choice></div></StepBlock>}</div>{mutationError && <p className="mt-4 rounded-xl bg-[var(--rose-soft)] px-3 py-2 text-sm text-[var(--rose)]">{mutationError.message}</p>}<div className="mt-8 flex justify-between border-t border-[var(--line)] pt-5"><Button type="button" variant="ghost" disabled={step === 0} onClick={() => setStep((current) => current - 1)}><BackIcon size={15} />{t("back")}</Button>{step === steps.length - 1 ? <Button type="submit" disabled={mutationPending}>{mutationPending ? <LoaderCircle size={15} className="animate-spin" /> : <Plus size={15} />}{isEditing ? t("save") : t("finish")}</Button> : <Button type="button" onClick={() => void next()}>{t("next")}<NextIcon size={15} /></Button>}</div></form></Card></div></div></div>;
}

function StepBlock({ eyebrow, title, children }: { eyebrow: string; title: string; children: React.ReactNode }) { return <div><p className="text-xs font-bold uppercase tracking-[.14em] text-[var(--accent)]">{eyebrow}</p><h2 className="mt-3 text-3xl font-black tracking-[-.05em] text-[var(--ink)]">{title}</h2><div className="mt-8">{children}</div></div>; }
function Choice({ children, selected, onClick, compact = false }: { children: React.ReactNode; selected: boolean; onClick: () => void; compact?: boolean }) { return <button type="button" onClick={onClick} className={cn("focus-ring flex items-center gap-3 rounded-2xl border text-start text-sm font-bold transition", compact ? "px-3 py-2.5" : "px-4 py-4", selected ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]" : "border-[var(--line)] bg-[var(--card)] text-[var(--muted)] hover:border-[var(--accent)]/60 hover:text-[var(--ink)]")}>{selected ? <span className="grid size-5 shrink-0 place-items-center rounded-full bg-[var(--accent)] text-white"><Check size={12} /></span> : <span className="size-5 shrink-0 rounded-full border border-[var(--line)]" />}{children}</button>; }
function ErrorText({ text }: { text?: string }) { return text ? <p className="mt-2 text-xs font-semibold text-[var(--rose)]">{text}</p> : null; }
