import { Component, type ErrorInfo, type ReactNode } from "react";
import { RefreshCcw, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Last-resort safety net for the routed page content. Without this, any
 * unhandled render error (e.g. a backend/LLM response that doesn't match the
 * expected shape reaching an unguarded .map()) unmounts the entire React
 * tree -- a blank white screen with no message, the worst possible failure
 * mode for a live demo recording. This catches it, keeps the sidebar/navbar
 * (rendered outside this boundary) usable, and shows what actually broke.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Spandana UI crashed:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-[50vh] flex-col items-center justify-center rounded-2xl border border-critical/30 bg-critical/5 px-6 py-14 text-center">
          <div className="mb-3 grid h-12 w-12 place-items-center rounded-full bg-critical/10 text-critical">
            <TriangleAlert size={22} />
          </div>
          <p className="text-lg text-foreground">This page hit an unexpected error</p>
          <p className="mt-1 max-w-md text-sm text-muted">{this.state.error.message}</p>
          <Button
            variant="secondary"
            size="sm"
            className="mt-4"
            onClick={() => this.setState({ error: null })}
          >
            <RefreshCcw size={15} /> Try again
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
