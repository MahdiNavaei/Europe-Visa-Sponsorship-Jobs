import { CompanyDetailPage } from "@/features/companies/company-detail-page";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <CompanyDetailPage id={Number(id)} />;
}
