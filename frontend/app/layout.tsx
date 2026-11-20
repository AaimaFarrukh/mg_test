import "./globals.css";

export const metadata = { title: "MG Apparel | Order Portal", description: "Customer order management portal" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

