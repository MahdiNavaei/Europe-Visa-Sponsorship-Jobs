import { notFound } from "next/navigation";
import { Providers } from "@/components/providers";
import { AppShell } from "@/components/layouts/app-shell";
import { isLocale, locales, type Locale } from "@/lib/i18n/messages";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({ children, params }: Readonly<{ children: React.ReactNode; params: Promise<{ locale: string }> }>) {
  const { locale: rawLocale } = await params;
  if (!isLocale(rawLocale)) notFound();
  const locale = rawLocale as Locale;
  return (
    <Providers locale={locale}>
      <div lang={locale} dir={locale === "fa" ? "rtl" : "ltr"} className="min-h-screen">
        <AppShell locale={locale}>{children}</AppShell>
      </div>
    </Providers>
  );
}
