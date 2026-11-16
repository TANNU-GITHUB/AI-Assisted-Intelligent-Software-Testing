'use client';

import { ReactNode } from 'react';
import {
  ThemeProvider as NextThemesProvider,
  useTheme as useNextTheme,
} from 'next-themes';

type Theme = 'dark' | 'light';

export function useTheme() {
  const { theme, setTheme } = useNextTheme();
  const currentTheme: Theme = theme === 'light' ? 'light' : 'dark';

  return {
    theme: currentTheme,
    toggleTheme: () => setTheme(currentTheme === 'dark' ? 'light' : 'dark'),
  };
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem={false}
      storageKey="bugai-theme"
    >
      {children}
    </NextThemesProvider>
  );
}
