import './globals.css';
import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { Navbar } from '@/components/navigation/Navbar';
import { CustomCursor } from '@/components/navigation/CustomCursor';
import { BackgroundGrid } from '@/components/navigation/BackgroundGrid';
import { PageTransition } from '@/components/navigation/PageTransition';
import { SmoothScrollProvider } from '@/components/navigation/SmoothScrollProvider';
import { ThemeProvider } from '@/components/navigation/ThemeProvider';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'BUG/AI — AI-Assisted Intelligent Software Testing',
  description:
    'AI-powered software testing that analyzes requirements, understands source code, generates test cases, executes them, and turns failures into actionable reports.',
  openGraph: {
    title: 'BUG/AI — AI-Assisted Intelligent Software Testing',
    description:
      'Find bugs before your users do. AI-assisted software testing with 3D visualization.',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // Start with 'dark' class; ThemeProvider will update it client-side
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrains.variable} font-sans antialiased`}
      >
        <ThemeProvider>
          <SmoothScrollProvider>
            <CustomCursor />
            <BackgroundGrid />
            <Navbar />
            <PageTransition>{children}</PageTransition>
          </SmoothScrollProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
