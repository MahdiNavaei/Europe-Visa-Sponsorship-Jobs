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
  const direction = locale === "fa" ? "rtl" : "ltr";
  return (
    <Providers locale={locale}>
      <script dangerouslySetInnerHTML={{ __html: `document.documentElement.lang=${JSON.stringify(locale)};document.documentElement.dir=${JSON.stringify(direction)};` }} />
      <div lang={locale} dir={direction} className="min-h-screen">
        <AppShell locale={locale}>{children}</AppShell>
      </div>
    </Providers>
  );
}
