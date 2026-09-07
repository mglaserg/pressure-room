import './globals.css';

export const metadata = {
  title: 'Pressure Room',
  description: 'Stories reveal character under pressure.',
  manifest: '/manifest.webmanifest',
};

export const viewport = {
  themeColor: '#0b0c0d',
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
