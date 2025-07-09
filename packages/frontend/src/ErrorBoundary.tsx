import { Component } from 'react';
import type { ReactNode } from 'react';
import { UI_TEXT } from './constants';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  public componentDidCatch() {
    // Error logged to browser's error reporting
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>{UI_TEXT.ERROR_BOUNDARY_TITLE}</h2>
          <p>{UI_TEXT.ERROR_BOUNDARY_MESSAGE}</p>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;