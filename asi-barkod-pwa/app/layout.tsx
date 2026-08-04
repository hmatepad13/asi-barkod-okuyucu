import type { Metadata, Viewport } from "next";
import "./globals.css";

const origin = "https://asi-barkod-pwa.vercel.app";
const description =
  "Android ve iPhone ile GS1 DataMatrix ve QR aşı barkodlarını Aşı Barkod PC alıcısına internet üzerinden gönderir.";

export const metadata: Metadata = {
  metadataBase: new URL(origin),
  title: "Aşı Barkod PWA",
  description,
  applicationName: "Aşı Barkod PWA",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Aşı Barkod PWA",
  },
  icons: {
    icon: "/icon-512.png",
    apple: "/icon-512.png",
  },
  openGraph: {
    title: "Aşı Barkod PWA",
    description,
    images: ["/og.png"],
    type: "website",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#080a0d",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
