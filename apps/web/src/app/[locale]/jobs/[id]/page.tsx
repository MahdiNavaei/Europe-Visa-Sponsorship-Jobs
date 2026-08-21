import { JobDetailPage } from "@/features/jobs/job-detail-page";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <JobDetailPage id={Number(id)} />;
}
