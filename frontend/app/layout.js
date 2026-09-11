import { Courier_Prime, Inter, Newsreader } from 'next/font/google';
import './globals.css';

const uiFont = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-pressure-ui',
  display: 'swap',
});

const displayFont = Newsreader({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  style: ['normal', 'italic'],
  variable: '--font-pressure-display',
  display: 'swap',
});

const screenplayFont = Courier_Prime({
  subsets: ['latin'],
  weight: ['400', '700'],
  variable: '--font-pressure-script',
  display: 'swap',
});

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
    <html lang="en" className={`${uiFont.variable} ${displayFont.variable} ${screenplayFont.variable}`}>
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
