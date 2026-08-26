import { Component, ErrorInfo, ReactNode } from 'react';
import i18n from '../../i18n/config';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <h2 className="text-xl font-bold text-slate-900 mb-2">
            {i18n.t('errors.somethingWentWrong')}
          </h2>
          <p className="text-sm text-slate-600 mb-6 max-w-md">
            {this.state.error?.message || i18n.t('errors.unexpectedError')}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false });
              window.location.reload();
            }}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
          >
            {i18n.t('errors.reloadPage')}
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
