import {Component, type ReactNode} from 'react';

type Props = {children: ReactNode; recover: () => void};
export default class WorkspaceBoundary extends Component<Props, {failed: boolean}> {
  state = {failed: false};

  static getDerivedStateFromError() {
    return {failed: true};
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return <section className="workflow card" role="alert">
      <h2>This workspace could not be displayed</h2>
      <p>Your saved project is retained. Retry this screen or return to Measurements.</p>
      <div className="actions">
        <button onClick={() => this.setState({failed: false})}>Retry workspace</button>
        <button onClick={this.props.recover}>Return to Measurements</button>
      </div>
    </section>;
  }
}
