'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bug, Menu, X, LogOut, User } from 'lucide-react';
import { useTheme } from './ThemeProvider';
import { fetchCurrentUser, logout, type PublicUser } from '@/lib/auth';

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
  const [user, setUser] = useState<PublicUser | null>(null);
  const pathname = usePathname();
  const { toggleTheme } = useTheme();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    fetchCurrentUser()
      .then(setUser)
      .catch(() => setUser(null));
  }, [pathname]);

  function handleLogout() {
    logout();
    setUser(null);
    window.location.href = '/login';
  }

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
              ? 'mt-2 max-w-5xl bg-white/80 dark:bg-black/80 backdrop-blur-xl border border-amber-500/20 dark:border-yellow-500/10 shadow-lg shadow-amber-500/5 dark:shadow-none'
              : 'max-w-7xl bg-transparent'
          } rounded-full px-4 sm:px-6`}
        >
          <nav className="flex items-center justify-between h-14">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="relative w-8 h-8 flex items-center justify-center">
                <Bug className="w-5 h-5 text-yellow-500 group-hover:rotate-12 transition-transform duration-300" />
                <div className="absolute inset-0 bg-yellow-500/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <span className="font-mono text-sm font-bold tracking-wider text-slate-800 dark:text-white">
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
                    className="relative px-4 py-2 text-sm transition-colors text-slate-500 dark:text-neutral-400 hover:text-slate-800 dark:hover:text-white"
                  >
                    {active && (
                      <motion.div
                        layoutId="nav-active"
                        className="absolute inset-0 rounded-full bg-amber-500/15 dark:bg-yellow-500/10"
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
                aria-label="Toggle theme"
                title="Toggle theme"
                className="relative flex items-center justify-center w-9 h-9 rounded-full border transition-all duration-300 group border-amber-400/40 dark:border-yellow-500/20 bg-amber-50 dark:bg-yellow-500/5 hover:bg-amber-100 dark:hover:bg-yellow-500/10 hover:border-amber-400 dark:hover:border-yellow-500/40"
              >
                <motion.div
                  initial={{ rotate: -180, scale: 0, opacity: 0 }}
                  animate={{ rotate: 0, scale: 1, opacity: 1 }}
                  transition={{ duration: 0.4, ease: 'easeOut' }}
                  className="relative"
                >
                  <Bug
                    className="w-4 h-4 transition-colors text-amber-600 dark:text-yellow-400 group-hover:text-amber-700 dark:group-hover:text-yellow-300"
                  />
                  {/* Mode indicator dot */}
                  <span
                    className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full border-2 bg-sky-400 dark:bg-slate-600 border-amber-50 dark:border-slate-900"
                  />
                </motion.div>
                {/* Glow */}
                <div className="absolute inset-0 rounded-full blur-md opacity-0 group-hover:opacity-60 transition-opacity bg-amber-400/30 dark:bg-yellow-500/20" />
              </button>

              {user ? (
                <>
                  <span className="flex items-center gap-1.5 text-xs text-neutral-400 max-w-[8rem] truncate">
                    <User className="w-3.5 h-3.5 shrink-0" />
                    {user.username}
                  </span>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="flex items-center gap-1.5 px-3 py-2 text-xs text-neutral-400 hover:text-white transition-colors"
                    aria-label="Sign out"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    Sign out
                  </button>
                  <Link
                    href="/live-lab"
                    className="flex items-center gap-2 px-5 py-2 text-sm font-medium text-black bg-yellow-500 rounded-full hover:bg-yellow-400 transition-colors group"
                  >
                    Live Lab
                    <span className="group-hover:translate-x-0.5 transition-transform">→</span>
                  </Link>
                </>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="px-4 py-2 text-sm text-neutral-300 hover:text-white transition-colors"
                  >
                    Sign in
                  </Link>
                  <Link
                    href="/live-lab"
                    className="flex items-center gap-2 px-5 py-2 text-sm font-medium text-black bg-yellow-500 rounded-full hover:bg-yellow-400 transition-colors group"
                  >
                    Start Testing
                    <span className="group-hover:translate-x-0.5 transition-transform">→</span>
                  </Link>
                </>
              )}
            </div>

            <div className="flex md:hidden items-center gap-2">
              {/* Mobile theme toggle */}
              <button
                id="theme-toggle-mobile"
                onClick={toggleTheme}
                aria-label="Toggle theme"
                title="Toggle theme"
                className="relative flex items-center justify-center w-9 h-9 rounded-full border transition-all duration-300 group border-amber-400/40 dark:border-yellow-500/20 bg-amber-50 dark:bg-yellow-500/5"
              >
                <motion.div
                  initial={{ rotate: -180, scale: 0 }}
                  animate={{ rotate: 0, scale: 1 }}
                  transition={{ duration: 0.4 }}
                >
                  <Bug
                    className="w-4 h-4 text-amber-600 dark:text-yellow-400"
                  />
                </motion.div>
                <span
                  className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full border-2 bg-sky-400 dark:bg-slate-600 border-amber-50 dark:border-slate-900"
                />
              </button>

              <button
                className="p-2 text-slate-700 dark:text-white"
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
            className="fixed inset-0 z-40 backdrop-blur-xl pt-20 px-6 md:hidden bg-white/95 dark:bg-black/95"
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
                        : 'text-slate-500 dark:text-neutral-400 hover:text-slate-800 dark:hover:text-white'
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
              {user ? (
                <button
                  type="button"
                  onClick={handleLogout}
                  className="mt-4 px-4 py-3 text-center text-neutral-300 border border-yellow-500/20 rounded-lg"
                >
                  Sign out ({user.username})
                </button>
              ) : (
                <Link
                  href="/login"
                  className="mt-4 px-4 py-3 text-center text-neutral-300 border border-yellow-500/20 rounded-lg"
                >
                  Sign in
                </Link>
              )}
              <Link
                href="/live-lab"
                className="mt-2 px-4 py-3 text-center text-black bg-yellow-500 rounded-lg font-medium"
              >
                Live Lab →
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
