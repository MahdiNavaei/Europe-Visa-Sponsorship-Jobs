import { notFound } from "next/navigation";
import "@/app/globals.css";
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
    <html lang={locale} dir={direction} suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Vazirmatn:wght@400;500;600;700;800;900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className={locale === "fa" ? "font-fa" : "font-en"}>
        <Providers locale={locale}>
          <AppShell locale={locale}>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
