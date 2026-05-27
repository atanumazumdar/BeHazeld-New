import type { Metadata, Viewport } from "next";
import { Header } from "@/components/layout/Header";
import { PWARegister } from "@/components/pwa/PWARegister";
import "./globals.css";

export const metadata: Metadata = {
  applicationName: "BeHazel'd",
  title: "BeHazel'd | Luxury Couture Atelier",
  description:
    "An exclusive Indian fashion house creating handcrafted couture, heirloom occasionwear, and pieces handpicked from the largest Chikankari market in the world.",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "BeHazel'd",
  },
  icons: {
    icon: "/Logo.png",
    apple: "/Logo.png",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#120A05",
};

type RootLayoutProps = {
  children: React.ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>
        <PWARegister />
        <Header />
        {children}
      </body>
    </html>
  );
}
