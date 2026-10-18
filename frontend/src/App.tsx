import { RouterProvider } from 'react-router-dom';
import { IdentityScopedQueryProvider } from './query/IdentityScopedQueryProvider';
import { router } from './routes';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import './i18n/config';

export default function App() {
  return (
    <ErrorBoundary>
      <IdentityScopedQueryProvider>
        <RouterProvider router={router} />
      </IdentityScopedQueryProvider>
    </ErrorBoundary>
  );
}
