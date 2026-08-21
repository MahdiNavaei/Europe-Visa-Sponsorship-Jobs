import type { Metadata } from "next";
import { Inter, Vazirmatn } from "next/font/google";
import { notFound } from "next/navigation";
import "@/app/globals.css";
import { AppShell } from "@/components/layouts/app-shell";
import { Providers } from "@/components/providers";
import { isLocale, locales, type Locale } from "@/lib/i18n/messages";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

const vazirmatn = Vazirmatn({
  subsets: ["arabic"],
  display: "swap",
  variable: "--font-vazirmatn",
});

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Readonly<{ params: Promise<{ locale: string }> }>): Promise<Metadata> {
  const { locale: rawLocale } = await params;
  if (!isLocale(rawLocale)) return {};
  const isPersian = rawLocale === "fa";
  return {
    title: isPersian
      ? "رادار شغلی اروپا | فرصت‌های واقعی اسپانسر ویزا"
      : "Career Radar | European Visa Sponsorship Jobs",
    description: isPersian
      ? "فرصت‌های شغلی فناوری در اروپا را با شواهد شفاف اسپانسر ویزا، امتیاز تطابق و تحلیل قابل توضیح پیدا کنید."
      : "Find European tech jobs with transparent visa-sponsorship evidence, explainable match scores, and relocation-focused career intelligence.",
    applicationName: "Career Radar",
    robots: { index: true, follow: true },
  };
}

export default async function LocaleLayout({ children, params }: Readonly<{ children: React.ReactNode; params: Promise<{ locale: string }> }>) {
  const { locale: rawLocale } = await params;
  if (!isLocale(rawLocale)) notFound();
  const locale = rawLocale as Locale;
  const direction = locale === "fa" ? "rtl" : "ltr";
  return (
    <html
      lang={locale}
      dir={direction}
      data-scroll-behavior="smooth"
      suppressHydrationWarning
      className={`${inter.variable} ${vazirmatn.variable}`}
    >
      <body className={locale === "fa" ? "font-fa" : "font-en"}>
        <Providers locale={locale}>
          <AppShell locale={locale}>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
