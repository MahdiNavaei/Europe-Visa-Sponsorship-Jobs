import "@/app/globals.css";

export default function RootRedirectLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" dir="ltr">
      <body className="font-en">{children}</body>
    </html>
  );
}
