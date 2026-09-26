'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bug, Menu, X, Sun, Moon } from 'lucide-react';
import { useTheme } from './ThemeProvider';

const navItems = [
  { label: 'Home', href: '/' },
  { label: 'How It Works', href: '/how-it-works' },
  { label: 'Live Lab', href: '/live-lab' },
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'About', href: '/about' },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();
  const isLight = theme === 'light';

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  return (
    <>
      <motion.header
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="fixed top-0 left-0 right-0 z-50"
      >
        <div
          className={`mx-auto transition-all duration-300 ${
            scrolled
              ? isLight
                ? 'mt-2 max-w-5xl bg-white/80 backdrop-blur-xl border border-amber-500/20 shadow-lg shadow-amber-500/5'
                : 'mt-2 max-w-5xl bg-black/80 backdrop-blur-xl border border-yellow-500/10'
              : 'max-w-7xl bg-transparent'
          } rounded-full px-4 sm:px-6`}
        >
          <nav className="flex items-center justify-between h-14">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="relative w-8 h-8 flex items-center justify-center">
                <Bug className="w-5 h-5 text-yellow-500 group-hover:rotate-12 transition-transform duration-300" />
                <div className="absolute inset-0 bg-yellow-500/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <span className={`font-mono text-sm font-bold tracking-wider ${isLight ? 'text-slate-800' : 'text-white'}`}>
                BUG<span className="text-yellow-500">/</span>AI
              </span>
            </Link>

            <div className="hidden md:flex items-center gap-1">
              {navItems.map((item) => {
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`relative px-4 py-2 text-sm transition-colors ${
                      isLight
                        ? 'text-slate-500 hover:text-slate-800'
                        : 'text-neutral-400 hover:text-white'
                    }`}
                  >
                    {active && (
                      <motion.div
                        layoutId="nav-active"
                        className={`absolute inset-0 rounded-full ${
                          isLight ? 'bg-amber-500/15' : 'bg-yellow-500/10'
                        }`}
                        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                      >
                        <div className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-yellow-500" />
                      </motion.div>
                    )}
                    <span className={active ? 'text-yellow-500' : ''}>
                      {item.label}
                    </span>
                  </Link>
                );
              })}
            </div>

            <div className="hidden md:flex items-center gap-3">
              {/* Theme toggle — Bug icon */}
              <button
                id="theme-toggle"
                onClick={toggleTheme}
                aria-label={isLight ? 'Switch to dark mode' : 'Switch to light mode'}
                title={isLight ? 'Switch to dark mode' : 'Switch to light mode'}
                className={`relative flex items-center justify-center w-9 h-9 rounded-full border transition-all duration-300 group ${
                  isLight
                    ? 'border-amber-400/40 bg-amber-50 hover:bg-amber-100 hover:border-amber-400'
                    : 'border-yellow-500/20 bg-yellow-500/5 hover:bg-yellow-500/10 hover:border-yellow-500/40'
                }`}
              >
                <motion.div
                  key={theme}
                  initial={{ rotate: -180, scale: 0, opacity: 0 }}
                  animate={{ rotate: 0, scale: 1, opacity: 1 }}
                  transition={{ duration: 0.4, ease: 'easeOut' }}
                  className="relative"
                >
                  <Bug
                    className={`w-4 h-4 transition-colors ${
                      isLight
                        ? 'text-amber-600 group-hover:text-amber-700'
                        : 'text-yellow-400 group-hover:text-yellow-300'
                    }`}
                  />
                  {/* Mode indicator dot */}
                  <span
                    className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full border-2 ${
                      isLight
                        ? 'bg-sky-400 border-amber-50'
                        : 'bg-slate-600 border-slate-900'
                    }`}
                  />
                </motion.div>
                {/* Glow */}
                <div className={`absolute inset-0 rounded-full blur-md opacity-0 group-hover:opacity-60 transition-opacity ${
                  isLight ? 'bg-amber-400/30' : 'bg-yellow-500/20'
                }`} />
              </button>

              <Link
                href="/live-lab"
                className="flex items-center gap-2 px-5 py-2 text-sm font-medium text-black bg-yellow-500 rounded-full hover:bg-yellow-400 transition-colors group"
              >
                Start Testing
                <span className="group-hover:translate-x-0.5 transition-transform">→</span>
              </Link>
            </div>

            <div className="flex md:hidden items-center gap-2">
              {/* Mobile theme toggle */}
              <button
                id="theme-toggle-mobile"
                onClick={toggleTheme}
                aria-label={isLight ? 'Switch to dark mode' : 'Switch to light mode'}
                className={`relative flex items-center justify-center w-9 h-9 rounded-full border transition-all duration-300 group ${
                  isLight
                    ? 'border-amber-400/40 bg-amber-50'
                    : 'border-yellow-500/20 bg-yellow-500/5'
                }`}
              >
                <motion.div
                  key={`mobile-${theme}`}
                  initial={{ rotate: -180, scale: 0 }}
                  animate={{ rotate: 0, scale: 1 }}
                  transition={{ duration: 0.4 }}
                >
                  <Bug
                    className={`w-4 h-4 ${isLight ? 'text-amber-600' : 'text-yellow-400'}`}
                  />
                </motion.div>
                <span
                  className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full border-2 ${
                    isLight ? 'bg-sky-400 border-amber-50' : 'bg-slate-600 border-slate-900'
                  }`}
                />
              </button>

              <button
                className={`p-2 ${isLight ? 'text-slate-700' : 'text-white'}`}
                onClick={() => setMobileOpen(!mobileOpen)}
                aria-label="Toggle menu"
              >
                {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
            </div>
          </nav>
        </div>
      </motion.header>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className={`fixed inset-0 z-40 backdrop-blur-xl pt-20 px-6 md:hidden ${
              isLight ? 'bg-white/95' : 'bg-black/95'
            }`}
          >
            <div className="flex flex-col gap-2">
              {navItems.map((item) => {
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`px-4 py-3 text-lg rounded-lg transition-colors ${
                      active
                        ? 'text-yellow-500 bg-yellow-500/10'
                        : isLight
                        ? 'text-slate-500 hover:text-slate-800'
                        : 'text-neutral-400 hover:text-white'
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
              <Link
                href="/live-lab"
                className="mt-4 px-4 py-3 text-center text-black bg-yellow-500 rounded-lg font-medium"
              >
                Start Testing →
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
