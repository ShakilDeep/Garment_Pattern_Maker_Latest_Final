import { Component, type ReactNode } from "react";

interface Props { children: ReactNode; label: string }
interface State { error: string | null }

/** Keeps the rest of the app usable if a view (e.g. WebGL) fails to load. */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };
  static getDerivedStateFromError(e: unknown): State {
    return { error: e instanceof Error ? e.message : String(e) };
  }
  render() {
    if (this.state.error) {
      return (
        <div className="banner err" role="alert" data-testid="view-error">
          {this.props.label} failed to load: {this.state.error}
          <button onClick={() => this.setState({ error: null })} aria-label="Retry">↻</button>
        </div>
      );
    }
    return this.props.children;
  }
}
