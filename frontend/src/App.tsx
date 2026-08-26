import { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { useThemeStore } from './store/themeStore';
import { queryClient } from './query/client';
import { router } from './routes';
import './i18n/config';

export default function App() {
  const { mode } = useThemeStore();

  useEffect(() => {
    // The .dark rules in index.css are plain descendant selectors (e.g.
    // ".dark body", ".dark .card-lg"), so the class has to live on <html>
    // - an ancestor of <body> - not on a div inside it, or "body" can
    // never match as a descendant of its own child.
    document.documentElement.classList.toggle('dark', mode === 'dark');
  }, [mode]);

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
