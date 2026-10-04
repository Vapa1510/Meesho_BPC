import type { Metadata, Viewport } from 'next';

import { AppShell } from '@/components/AppShell';
import { BrandProvider } from '@/components/BrandContext';
import { CreatorProvider } from '@/components/CreatorContext';
import './globals.css';

export const metadata: Metadata = {
  title: 'Fit Engine — creators and products, matched',
  description:
    'Ranks BPC products for creators on audience, niche, intent, quality, commerce and trend — and shows the working behind every score.',
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
