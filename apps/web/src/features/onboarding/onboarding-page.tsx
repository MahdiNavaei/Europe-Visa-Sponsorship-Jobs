/* eslint-disable react-hooks/incompatible-library -- React Hook Form exposes intentionally mutable helpers; React Compiler safely opts this component out of memoization. */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, ArrowRight, Check, LoaderCircle, MapPin, Plus, Search, Sparkles } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCandidate, useCreateCandidate, useUpdateCandidate } from "@/lib/api/hooks";
import { cn } from "@/lib/utils/cn";
import { setCandidateId, useCandidateId } from "@/lib/utils/candidate";
import { formatCountry } from "@/lib/utils/format";
import { candidateSchema, type CandidateFormValues } from "@/lib/validators/candidate";

const roles = [
  "Software Engineering",
  "Backend Engineering",
  "Frontend Engineering",
  "Full Stack Engineering",
  "Mobile Engineering",
  "QA / Test Automation",
  "Security Engineering",
  "Machine Learning Engineer",
  "Senior Machine Learning Engineer",
  "AI Engineer",
  "Senior AI Engineer",
  "Applied Scientist",
  "Data Scientist",
  "ML Platform Engineer",
  "MLOps Engineer",
  "Generative AI Engineer",
  "LLM Engineer",
  "AI / Machine Learning",
  "Data Science",
  "Data Engineering",
  "DevOps / Cloud",
];

type SkillGroup = {
  key: string;
  label: string;
  labelFa: string;
  skills: string[];
};

const skillGroups: SkillGroup[] = [
  {
    key: "programming",
    label: "Programming languages",
    labelFa: "زبان های برنامه نویسی",
    skills: ["Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#", "Kotlin", "Swift", "PHP", "Ruby", "Scala", "Bash"],
  },
  {
    key: "backend",
    label: "Backend",
    labelFa: "بک اند",
    skills: ["Node.js", "Express.js", "NestJS", "Django", "FastAPI", "Flask", "Spring", ".NET", "ASP.NET Core", "Laravel", "Ruby on Rails", "GraphQL", "gRPC"],
  },
  {
    key: "frontend",
    label: "Frontend",
    labelFa: "فرانت اند",
    skills: ["React", "Next.js", "Vue.js", "Angular", "Svelte", "Redux", "Tailwind CSS"],
  },
  {
    key: "mobile",
    label: "Mobile",
    labelFa: "موبایل",
    skills: ["Android", "iOS", "Flutter", "React Native"],
  },
  {
    key: "data",
    label: "Data & databases",
    labelFa: "داده و دیتابیس",
    skills: ["SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Snowflake", "BigQuery", "Databricks", "Kafka", "RabbitMQ", "Spark", "Airflow", "dbt", "Pandas", "NumPy"],
  },
  {
    key: "machine_learning",
    label: "AI / Machine Learning",
    labelFa: "هوش مصنوعی / یادگیری ماشین",
    skills: ["Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "scikit-learn", "LLM", "RAG", "Natural Language Processing", "Computer Vision", "Hugging Face", "Transformers", "LangChain", "LangGraph", "MLflow", "MLOps"],
  },
  {
    key: "cloud",
    label: "Cloud / DevOps",
    labelFa: "کلاد / DevOps",
    skills: ["Docker", "Kubernetes", "Helm", "AWS", "Azure", "Google Cloud", "Terraform", "Ansible", "CI/CD", "GitHub Actions", "Jenkins", "Argo CD", "Linux", "Git"],
  },
  {
    key: "testing",
    label: "Testing",
    labelFa: "تست",
    skills: ["pytest", "Jest", "Playwright", "Cypress", "Selenium"],
  },
  {
    key: "observability",
    label: "Observability",
    labelFa: "مانیتورینگ و مشاهده پذیری",
    skills: ["Prometheus", "Grafana", "OpenTelemetry", "Datadog"],
  },
  {
    key: "security",
    label: "Security",
    labelFa: "امنیت",
    skills: ["OAuth", "OpenID Connect"],
  },
];

const countries = ["Germany", "Netherlands", "Sweden", "Denmark", "Finland", "Ireland", "United Kingdom"];
const steps = ["role", "skills", "experience", "countries", "visa", "remote"] as const;

const roleLabelsFa: Record<string, string> = {
  "Software Engineering": "مهندسی نرم افزار",
  "Backend Engineering": "مهندسی بک اند",
  "Frontend Engineering": "مهندسی فرانت اند",
  "Full Stack Engineering": "مهندسی فول استک",
  "Mobile Engineering": "مهندسی موبایل",
  "QA / Test Automation": "تست و اتوماسیون QA",
  "Security Engineering": "مهندسی امنیت",
  "AI / Machine Learning": "هوش مصنوعی / یادگیری ماشین",
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

function priorityKeys(selectedRoles: string[]) {
  const text = selectedRoles.join(" ").toLowerCase();
  const keys: string[] = [];
  const add = (...values: string[]) => values.forEach((value) => !keys.includes(value) && keys.push(value));

  if (/machine learning|\bai\b|data scientist|applied scientist|llm|generative/.test(text)) add("machine_learning", "data", "programming", "cloud");
  if (/data engineering/.test(text)) add("data", "programming", "cloud", "backend");
  if (/backend/.test(text)) add("backend", "programming", "data", "cloud", "testing");
  if (/frontend/.test(text)) add("frontend", "programming", "testing");
  if (/full stack/.test(text)) add("backend", "frontend", "programming", "data", "testing");
  if (/mobile/.test(text)) add("mobile", "programming", "testing");
  if (/software engineering/.test(text)) add("programming", "backend", "frontend", "data", "cloud", "testing");
  if (/devops|cloud|mlops|platform/.test(text)) add("cloud", "observability", "programming", "data");
  if (/security/.test(text)) add("security", "cloud", "programming", "observability");
  if (/qa|test automation/.test(text)) add("testing", "programming", "frontend", "backend");

  return keys;
}

export function OnboardingPage() {
  const locale = useLocale();
  const t = useTranslations("onboarding");
  const router = useRouter();
  const candidateId = useCandidateId();
  const { data: existingCandidate } = useCandidate(candidateId);
  const isEditing = candidateId !== null && existingCandidate?.id === candidateId;
  const [hydrated, setHydrated] = useState(false);
  const [step, setStep] = useState(0);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const [skillQuery, setSkillQuery] = useState("");
  const createMutation = useCreateCandidate();
  const updateMutation = useUpdateCandidate();
  const mutationPending = createMutation.isPending || updateMutation.isPending;
  const mutationError = createMutation.error ?? updateMutation.error;
  const {
    register,
    handleSubmit,
    watch,
    getValues,
    setValue,
    trigger,
    reset,
    formState: { errors },
  } = useForm<CandidateFormValues>({ resolver: zodResolver(candidateSchema), defaultValues });

  useEffect(() => {
    setHydrated(true);
  }, []);

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

  const roleDisplay = useMemo(
    () => (value: string) => (locale === "fa" ? roleLabelsFa[value] ?? value : value),
    [locale],
  );

  const visibleSkillGroups = useMemo(() => {
    const priorities = priorityKeys(selectedRoles);
    const priorityIndex = new Map(priorities.map((key, index) => [key, index]));
    const query = skillQuery.trim().toLowerCase();
    return skillGroups
      .map((group) => ({
        ...group,
        skills: query ? group.skills.filter((skill) => skill.toLowerCase().includes(query)) : group.skills,
      }))
      .filter((group) => group.skills.length > 0)
      .sort((a, b) => (priorityIndex.get(a.key) ?? 100) - (priorityIndex.get(b.key) ?? 100));
  }, [selectedRoles, skillQuery]);

  const knownSkillNames = useMemo(
    () => new Set(skillGroups.flatMap((group) => group.skills).map((skill) => skill.toLowerCase())),
    [],
  );
  const legacySelectedSkills = selectedSkills.filter((skill) => !knownSkillNames.has(skill.toLowerCase()));

  const toggle = (field: "target_roles" | "skills" | "preferred_countries", value: string) => {
    const current = field === "target_roles" ? selectedRoles : field === "skills" ? selectedSkills : selectedCountries;
    const next = current.includes(value) ? current.filter((item) => item !== value) : [...current, value];
    if (field === "target_roles") setSelectedRoles(next);
    else if (field === "skills") setSelectedSkills(next);
    else setSelectedCountries(next);
    setValue(field, next, { shouldValidate: true });
  };

  const submit = async (values: CandidateFormValues) => {
    const candidate =
      isEditing && candidateId !== null
        ? await updateMutation.mutateAsync({ id: candidateId, input: values })
        : await createMutation.mutateAsync(values);
    if ("access_token" in candidate && typeof candidate.access_token === "string") {
      setCandidateId(candidate.id, candidate.access_token);
    } else if (!isEditing) {
      setCandidateId(candidate.id);
    }
    router.push(`/${locale}/dashboard`);
  };

  const next = () => {
    const fields = step === 0 ? ["name", "target_roles"] : step === 1 ? ["skills"] : step === 3 ? ["preferred_countries"] : [];
    const current = getValues();
    const valid =
      fields.length === 0 ||
      (step === 0 && current.name.trim().length > 0 && selectedRoles.length > 0) ||
      (step === 1 && selectedSkills.length > 0) ||
      (step === 3 && selectedCountries.length > 0);
    if (valid) setStep((currentStep) => Math.min(currentStep + 1, steps.length - 1));
    else void trigger(fields as (keyof CandidateFormValues)[]);
  };

  const BackIcon = locale === "fa" ? ArrowRight : ArrowLeft;
  const NextIcon = locale === "fa" ? ArrowLeft : ArrowRight;

  return (
    <div className="min-h-[calc(100vh-72px)] px-5 py-10 sm:px-8 lg:px-10 lg:py-16">
      <div className="mx-auto max-w-4xl">
        <Link href={`/${locale}`} className="focus-ring inline-flex items-center gap-2 text-sm font-bold text-[var(--muted)] hover:text-[var(--accent)]">
          <BackIcon size={15} />
          {t("back")}
        </Link>
        <div className="mt-8 grid gap-8 lg:grid-cols-[.7fr_1.3fr]">
          <aside className="rounded-3xl bg-[var(--ink)] p-7 text-[var(--paper)] sm:p-9">
            <div className="grid size-11 place-items-center rounded-2xl bg-white/10 text-[var(--accent)]"><Sparkles size={20} /></div>
            <p className="mt-8 text-xs font-bold uppercase tracking-[.15em] text-white/50">{t("profileLabel")}</p>
            <h1 className="mt-4 text-3xl font-black leading-tight tracking-[-.05em]">{t("title")}</h1>
            <p className="mt-4 text-sm leading-7 text-white/60">{isEditing ? t("editing") : t("subtitle")}</p>
            <div className="mt-10 space-y-3">
              {steps.map((item, index) => (
                <div key={item} className={cn("flex items-center gap-3 text-sm", index === step ? "font-bold text-white" : index < step ? "text-[var(--mint)]" : "text-white/35")}>
                  <span className={cn("grid size-7 place-items-center rounded-full border text-xs", index < step ? "border-[var(--mint)] bg-[var(--mint)] text-[var(--ink)]" : index === step ? "border-[var(--accent)] bg-[var(--accent)] text-white" : "border-white/20")}>
                    {index < step ? <Check size={13} /> : index + 1}
                  </span>
                  {t(item)}
                </div>
              ))}
            </div>
          </aside>

          <Card className="p-6 sm:p-9">
            <form data-hydrated={hydrated ? "true" : "false"} aria-busy={!hydrated} onSubmit={handleSubmit(submit)}>
              <div className="min-h-[390px]">
                {step === 0 && (
                  <StepBlock eyebrow={t("stepLabel")} title={t("role")}>
                    <label className="mb-6 block">
                      <span className="mb-2 block text-xs font-bold text-[var(--muted)]">{t("name")}</span>
                      <Input {...register("name")} placeholder={t("placeholder")} autoFocus disabled={!hydrated} />
                      {errors.name && <ErrorText text={errors.name.message} />}
                    </label>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {roles.map((role) => (
                        <Choice key={role} disabled={!hydrated} selected={selectedRoles.includes(role)} onClick={() => toggle("target_roles", role)}>
                          {roleDisplay(role)}
                        </Choice>
                      ))}
                    </div>
                    {errors.target_roles && <ErrorText text={errors.target_roles.message} />}
                  </StepBlock>
                )}

                {step === 1 && (
                  <StepBlock eyebrow={t("stepLabel")} title={t("skills")}>
                    <p className="mb-5 text-sm text-[var(--muted)]">{t("skillsHelp")}</p>
                    <label className="relative mb-6 block">
                      <Search size={16} className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
                      <Input
                        value={skillQuery}
                        onChange={(event) => setSkillQuery(event.target.value)}
                        className="ps-10"
                        placeholder={locale === "fa" ? "جستجوی مهارت..." : "Search skills..."}
                        disabled={!hydrated}
                      />
                    </label>
                    {legacySelectedSkills.length > 0 && !skillQuery && (
                      <div className="mb-6">
                        <p className="mb-3 text-xs font-black uppercase tracking-[.12em] text-[var(--muted)]">
                          {locale === "fa" ? "مهارت های قبلی پروفایل" : "Existing profile skills"}
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {legacySelectedSkills.map((skill) => (
                            <Choice key={skill} compact disabled={!hydrated} selected onClick={() => toggle("skills", skill)}>{skill}</Choice>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="space-y-7">
                      {visibleSkillGroups.map((group) => (
                        <div key={group.key}>
                          <p className="mb-3 text-xs font-black uppercase tracking-[.12em] text-[var(--muted)]">
                            {locale === "fa" ? group.labelFa : group.label}
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {group.skills.map((skill) => (
                              <Choice key={skill} compact disabled={!hydrated} selected={selectedSkills.includes(skill)} onClick={() => toggle("skills", skill)}>
                                {skill}
                              </Choice>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                    {visibleSkillGroups.length === 0 && (
                      <p className="py-8 text-center text-sm text-[var(--muted)]">
                        {locale === "fa" ? "مهارتی با این عبارت پیدا نشد." : "No skill matches this search."}
                      </p>
                    )}
                  </StepBlock>
                )}

                {step === 2 && (
                  <StepBlock eyebrow={t("stepLabel")} title={t("experience")}>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Choice disabled={!hydrated} selected={watch("seniority") === "junior"} onClick={() => setValue("seniority", "junior")}>{t("early")}</Choice>
                      <Choice disabled={!hydrated} selected={watch("seniority") === "mid"} onClick={() => setValue("seniority", "mid")}>{t("mid")}</Choice>
                      <Choice disabled={!hydrated} selected={watch("seniority") === "senior"} onClick={() => setValue("seniority", "senior")}>{t("senior")}</Choice>
                      <Choice disabled={!hydrated} selected={watch("seniority") === "staff"} onClick={() => setValue("seniority", "staff")}>{t("staff")}</Choice>
                    </div>
                    <label className="mt-8 block">
                      <span className="mb-2 block text-xs font-bold text-[var(--muted)]">{t("years")}</span>
                      <Input type="number" min="0" max="60" step="0.5" disabled={!hydrated} {...register("years_of_experience", { valueAsNumber: true })} />
                    </label>
                  </StepBlock>
                )}

                {step === 3 && (
                  <StepBlock eyebrow={t("stepLabel")} title={t("countries")}>
                    <p className="mb-5 text-sm text-[var(--muted)]">{t("countriesHelp")}</p>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {countries.map((country) => (
                        <Choice key={country} disabled={!hydrated} selected={selectedCountries.includes(country)} onClick={() => toggle("preferred_countries", country)}>
                          <MapPin size={15} />
                          {formatCountry(country, locale)}
                        </Choice>
                      ))}
                    </div>
                  </StepBlock>
                )}

                {step === 4 && (
                  <StepBlock eyebrow={t("stepLabel")} title={t("visa")}>
                    <div className="space-y-3">
                      <Choice disabled={!hydrated} selected={watch("visa_required") === true} onClick={() => setValue("visa_required", true)}>{t("visaYes")}</Choice>
                      <Choice disabled={!hydrated} selected={watch("visa_required") === false} onClick={() => setValue("visa_required", false)}>{t("visaNo")}</Choice>
                    </div>
                  </StepBlock>
                )}

                {step === 5 && (
                  <StepBlock eyebrow={t("stepLabel")} title={t("remote")}>
                    <div className="space-y-3">
                      <Choice disabled={!hydrated} selected={watch("remote_preference") === "preferred"} onClick={() => setValue("remote_preference", "preferred")}>{t("remotePreferred")}</Choice>
                      <Choice disabled={!hydrated} selected={watch("remote_preference") === "no_preference"} onClick={() => setValue("remote_preference", "no_preference")}>{t("remoteOpen")}</Choice>
                      <Choice disabled={!hydrated} selected={watch("remote_preference") === "required"} onClick={() => setValue("remote_preference", "required")}>{t("remoteRequired")}</Choice>
                    </div>
                  </StepBlock>
                )}
              </div>

              {mutationError && <p className="mt-4 rounded-xl bg-[var(--rose-soft)] px-3 py-2 text-sm text-[var(--rose)]">{mutationError.message}</p>}

              <div className="mt-8 flex justify-between border-t border-[var(--line)] pt-5">
                <Button type="button" variant="ghost" disabled={!hydrated || step === 0} onClick={() => setStep((current) => current - 1)}>
                  <BackIcon size={15} />
                  {t("back")}
                </Button>
                {step === steps.length - 1 ? (
                  <Button key="submit-profile" type="submit" disabled={!hydrated || mutationPending}>
                    {mutationPending ? <LoaderCircle size={15} className="animate-spin" /> : <Plus size={15} />}
                    {isEditing ? t("save") : t("finish")}
                  </Button>
                ) : (
                  <Button
                    key="continue-onboarding"
                    type="button"
                    disabled={!hydrated}
                    onClick={(event) => {
                      event.preventDefault();
                      next();
                    }}
                  >
                    {t("next")}
                    <NextIcon size={15} />
                  </Button>
                )}
              </div>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}

function StepBlock({ eyebrow, title, children }: { eyebrow: string; title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-[.14em] text-[var(--accent)]">{eyebrow}</p>
      <h2 className="mt-3 text-3xl font-black tracking-[-.05em] text-[var(--ink)]">{title}</h2>
      <div className="mt-8">{children}</div>
    </div>
  );
}

function Choice({ children, selected, onClick, compact = false, disabled = false }: { children: React.ReactNode; selected: boolean; onClick: () => void; compact?: boolean; disabled?: boolean }) {
  return (
    <button
      type="button"
      disabled={disabled}
      aria-pressed={selected}
      onClick={onClick}
      className={cn(
        "focus-ring flex items-center gap-3 rounded-2xl border text-start text-sm font-bold transition disabled:cursor-not-allowed disabled:opacity-60",
        compact ? "px-3 py-2.5" : "px-4 py-4",
        selected
          ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
          : "border-[var(--line)] bg-[var(--card)] text-[var(--muted)] hover:border-[var(--accent)]/60 hover:text-[var(--ink)]",
      )}
    >
      {selected ? (
        <span className="grid size-5 shrink-0 place-items-center rounded-full bg-[var(--accent)] text-white"><Check size={12} /></span>
      ) : (
        <span className="size-5 shrink-0 rounded-full border border-[var(--line)]" />
      )}
      {children}
    </button>
  );
}

function ErrorText({ text }: { text?: string }) {
  return text ? <p className="mt-2 text-xs font-semibold text-[var(--rose)]">{text}</p> : null;
}
