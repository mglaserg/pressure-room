import './globals.css';

export const metadata = {
  title: 'Pressure Room',
  description: 'Writers, under pressure.',
  manifest: '/manifest.webmanifest',
};

export const viewport = {
  themeColor: '#0a0b0d',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
