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
      <body>
        {children}
        <footer className="legal-footer" aria-label="Legal">
          <a href="/privacy">Privacy Policy</a>
          <a href="/terms">Terms of Service</a>
        </footer>
      </body>
    </html>
  );
}
