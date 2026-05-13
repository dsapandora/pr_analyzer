import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import '@/styles/globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'PR Analyzer — AI-Powered Pull Request Intelligence',
  description: 'Analyze GitHub Pull Requests with AI. Automatically cluster by topic, detect duplicates, score quality, and chat with your codebase.',
  keywords: ['GitHub', 'Pull Requests', 'AI', 'Code Review', 'Analysis'],
  authors: [{ name: 'PR Analyzer' }],
  openGraph: {
    title: 'PR Analyzer',
    description: 'AI-powered GitHub Pull Request analysis',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} antialiased min-h-screen bg-background text-foreground`}>
        {children}
      </body>
    </html>
  );
}
