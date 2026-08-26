import { RouterProvider } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { useThemeStore } from './store/themeStore';
import { queryClient } from './query/client';
import { router } from './routes';
import './i18n/config';

export default function App() {
  const { mode } = useThemeStore();

  return (
    <div className={mode === 'dark' ? 'dark' : ''}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </div>
  );
}
