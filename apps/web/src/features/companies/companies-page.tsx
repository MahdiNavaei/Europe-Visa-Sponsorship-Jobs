"use client";

import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Building2, ExternalLink, Globe2, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { PageHeading } from "@/components/common/page-heading";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useCompanies } from "@/lib/api/hooks";
import type { Company } from "@/lib/types";

const columnHelper = createColumnHelper<Company>();

export function CompaniesPage() {
  const c = useTranslations("common");
  const [query, setQuery] = useState("");
  const { data, isLoading, isError, refetch } = useCompanies();
  const filtered = useMemo(() => data?.filter((company) => `${company.name} ${company.country ?? ""}`.toLowerCase().includes(query.toLowerCase())) ?? [], [data, query]);
  const columns = useMemo(() => [columnHelper.accessor("name", { header: "Company", cell: (info) => <div className="flex items-center gap-3"><div className="grid size-9 place-items-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]"><Building2 size={16} /></div><span className="font-bold text-[var(--ink)]">{info.getValue()}</span></div> }), columnHelper.accessor("country", { header: "Country", cell: (info) => <span className="flex items-center gap-2 text-[var(--muted)]"><Globe2 size={14} />{info.getValue() ?? "Europe"}</span> }), columnHelper.accessor("sponsor_verified", { header: "Visa signal", cell: (info) => info.getValue() ? <Badge tone="success"><ShieldCheck size={12} />{c("verified")}</Badge> : <Badge tone="warning">Evidence review</Badge> }), columnHelper.accessor("career_url", { header: "Website", cell: (info) => info.getValue() ? <a className="focus-ring inline-flex items-center gap-1 text-xs font-bold text-[var(--accent)]" href={info.getValue() ?? "#"} target="_blank" rel="noreferrer">Open <ExternalLink size={13} /></a> : <span className="text-xs text-[var(--muted)]">—</span> })], [c]);
  const table = useReactTable({ data: filtered, columns, getCoreRowModel: getCoreRowModel() });
  return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-10 lg:py-14"><PageHeading eyebrow="Company intelligence" title="Signals behind the names" description="Explore companies present in the evidence-backed job index. A verified sponsor record is a positive signal—not a guarantee for every role." action={<div className="w-full sm:w-64"><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search companies" aria-label="Search companies" /></div>} /><div className="mt-10">{isLoading ? <div className="space-y-3"><Skeleton className="h-16" /><Skeleton className="h-16" /><Skeleton className="h-16" /></div> : isError ? <EmptyState title={c("unavailable")} body="Company intelligence will appear when the API is running." action={c("tryAgain")} onAction={() => void refetch()} /> : filtered.length === 0 ? <EmptyState title="No companies found" body="Try another search term." /> : <div className="overflow-hidden rounded-3xl border border-[var(--line)] bg-[var(--card)]"><div className="overflow-x-auto"><table className="w-full min-w-[650px] text-start"><thead className="border-b border-[var(--line)] bg-[var(--paper)]"><tr>{table.getHeaderGroups()[0].headers.map((header) => <th key={header.id} className="px-6 py-4 text-xs font-bold uppercase tracking-[.12em] text-[var(--muted)]">{flexRender(header.column.columnDef.header, header.getContext())}</th>)}</tr></thead><tbody>{table.getRowModel().rows.map((row) => <tr key={row.id} className="border-b border-[var(--line)] last:border-0 hover:bg-[var(--paper)]">{row.getVisibleCells().map((cell) => <td key={cell.id} className="px-6 py-5 text-sm">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>)}</tbody></table></div></div>}</div></div>;
}
