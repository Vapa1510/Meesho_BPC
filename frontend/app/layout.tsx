import type { Metadata, Viewport } from 'next';

import { AppShell } from '@/components/AppShell';
import { BrandProvider } from '@/components/BrandContext';
import { CreatorProvider } from '@/components/CreatorContext';
import './globals.css';

export const metadata: Metadata = {
  title: 'Fit Engine · Meesho DICE S3 · Team Pro',
  description:
    'Creator × Product Fit Engine: ranks BPC products for each creator on seven signals (audience, niche, intent, product, commerce, trend, brand) and explains every score. Prototype with sample data.',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#E8195F',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <CreatorProvider>
          <BrandProvider>
            <AppShell>{children}</AppShell>
          </BrandProvider>
        </CreatorProvider>
      </body>
    </html>
  );
}
