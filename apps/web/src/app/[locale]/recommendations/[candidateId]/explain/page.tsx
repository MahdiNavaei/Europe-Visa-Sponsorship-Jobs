import { ExplanationPage } from "@/features/recommendations/explanation-page";

export default async function Page({ params }: { params: Promise<{ candidateId: string }> }) {
  const { candidateId } = await params;
  return <ExplanationPage candidateId={Number(candidateId)} />;
}
