'use client';

import Link from 'next/link';
import { Bug } from 'lucide-react';

const links = {
  Product: [
    { label: 'Home', href: '/' },
    { label: 'How It Works', href: '/how-it-works' },
    { label: 'Live Lab', href: '/live-lab' },
    { label: 'Dashboard', href: '/dashboard' },
  ],
  Company: [
    { label: 'About', href: '/about' },
    { label: 'Methodology', href: '/about' },
    { label: 'Team', href: '/about' },
  ],
  Resources: [
    { label: 'Documentation', href: '/how-it-works' },
    { label: 'Test Types', href: '/how-it-works' },
    { label: 'Bug Hunt', href: '/' },
  ],
};

export function Footer() {
  return (
    <footer className="relative border-t border-border bg-background text-foreground transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6 sm:px-10 lg:px-20 py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {/* Logo */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2 mb-4">
              <Bug className="w-5 h-5 text-yellow-500" />
              <span className="font-mono text-sm font-bold tracking-wider text-foreground">
                BUG<span className="text-yellow-500">/</span>AI
              </span>
            </Link>
            <p className="text-sm max-w-xs text-muted-foreground">
              AI-assisted intelligent software testing. Find bugs before your users do.
            </p>
          </div>

          {/* Links */}
          {Object.entries(links).map(([category, items]) => (
            <div key={category}>
              <h4 className="font-mono text-xs text-yellow-500 uppercase tracking-widest mb-4">
                {category}
              </h4>
              <ul className="space-y-2">
                {items.map((item) => (
                  <li key={item.label}>
                    <Link
                      href={item.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-yellow-500"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 pt-8 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs font-mono text-muted-foreground">
            BUG/AI — FRONTEND DEMO — NO REAL AI BACKEND
          </p>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
            <span className="text-xs font-mono text-muted-foreground">
              SYSTEM ONLINE
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
