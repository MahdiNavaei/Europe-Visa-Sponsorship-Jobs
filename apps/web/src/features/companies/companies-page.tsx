/* eslint-disable react-hooks/incompatible-library -- TanStack Table exposes mutable helpers; React Compiler safely opts this component out of memoization. */
"use client";

import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { ArrowLeft, ArrowRight, Building2, ExternalLink, Globe2, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { PageHeading } from "@/components/common/page-heading";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useCompanies } from "@/lib/api/hooks";
import type { Company } from "@/lib/types";
import { formatCountry } from "@/lib/utils/format";

const columnHelper = createColumnHelper<Company>();

export function CompaniesPage() {
  const locale = useLocale();
  const c = useTranslations("common");
  const t = useTranslations("companies");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const { data: page, isLoading, isError, refetch } = useCompanies(query, offset);
  const data = page?.items ?? [];
  const columns = useMemo(
    () => [
      columnHelper.accessor("name", {
        header: t("company"),
        cell: (info) => (
          <Link href={`/${locale}/companies/${info.row.original.id}`} className="focus-ring flex items-center gap-3">
            <div className="grid size-9 place-items-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]"><Building2 size={16} /></div>
            <span className="flex flex-wrap items-center gap-2 font-bold text-[var(--ink)] hover:text-[var(--accent)]">{info.getValue()}{info.row.original.name_quality === "untrusted" && <Badge tone="warning">{t("identityReview")}</Badge>}</span>
          </Link>
        ),
      }),
      columnHelper.accessor("country", {
        header: t("country"),
        cell: (info) => <span className="flex items-center gap-2 text-[var(--muted)]"><Globe2 size={14} />{formatCountry(info.getValue(), locale)}</span>,
      }),
      columnHelper.accessor("registry_status", {
        header: t("registryEvidence"),
        cell: (info) => info.getValue() === "verified_registry"
          ? <Badge tone="success"><ShieldCheck size={12} />{t("registryMatched")}</Badge>
          : info.getValue() === "identity_untrusted"
            ? <Badge tone="warning">{t("identityReview")}</Badge>
            : <Badge tone="neutral">{t("registryNotFound")}</Badge>,
      }),
      columnHelper.accessor("job_sponsorship_status", {
        header: t("vacancyEvidence"),
        cell: (info) => info.getValue() === "confirmed_yes"
          ? <Badge tone="success">{t("vacancyYes")}</Badge>
          : info.getValue() === "confirmed_no"
            ? <Badge tone="warning">{t("vacancyNo")}</Badge>
            : info.getValue() === "conflicting"
              ? <Badge tone="warning">{t("vacancyConflicting")}</Badge>
              : <Badge tone="neutral">{t("vacancyNotMentioned")}</Badge>,
      }),
      columnHelper.accessor("career_url", {
        header: t("website"),
        cell: (info) => info.getValue()
          ? <a className="focus-ring inline-flex items-center gap-1 text-xs font-bold text-[var(--accent)]" href={info.getValue() ?? "#"} target="_blank" rel="noreferrer">{c("open")} <ExternalLink size={13} /></a>
          : <span className="text-xs text-[var(--muted)]">—</span>,
      }),
    ],
    [c, locale, t],
  );
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() });

  return (
    <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14">
      <PageHeading
        eyebrow={t("eyebrow")}
        title={t("title")}
        description={t("subtitle")}
        action={<div className="w-full sm:w-64"><Input value={query} onChange={(event) => { setQuery(event.target.value); setOffset(0); }} placeholder={t("search")} aria-label={t("search")} /></div>}
      />
      <div className="mt-10">
        {isLoading ? (
          <div className="space-y-3"><Skeleton className="h-16" /><Skeleton className="h-16" /><Skeleton className="h-16" /></div>
        ) : isError ? (
          <EmptyState title={c("unavailable")} body={t("unavailableBody")} action={c("tryAgain")} onAction={() => void refetch()} />
        ) : data.length === 0 ? (
          <EmptyState title={t("noCompanies")} body={t("trySearch")} />
        ) : (
          <div className="overflow-hidden rounded-3xl border border-[var(--line)] bg-[var(--card)]">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[650px] text-start">
                <thead className="border-b border-[var(--line)] bg-[var(--paper)]">
                  <tr>
                    {table.getHeaderGroups()[0].headers.map((header) => (
                      <th key={header.id} className="px-6 py-4 text-xs font-bold uppercase tracking-[.12em] text-[var(--muted)]">{flexRender(header.column.columnDef.header, header.getContext())}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table.getRowModel().rows.map((row) => (
                    <tr key={row.id} className="border-b border-[var(--line)] last:border-0 hover:bg-[var(--paper)]">
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-6 py-5 text-sm">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {!isLoading && !isError && page && page.total > 50 && <div className="mt-4 flex items-center justify-between text-sm text-[var(--muted)]"><span>{offset + 1}–{Math.min(offset + 50, page.total)} / {page.total}</span><div className="flex gap-2"><Button variant="secondary" size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}><ArrowLeft size={14} /></Button><Button variant="secondary" size="sm" disabled={offset + 50 >= page.total} onClick={() => setOffset(offset + 50)}><ArrowRight size={14} /></Button></div></div>}
      </div>
    </div>
  );
}
