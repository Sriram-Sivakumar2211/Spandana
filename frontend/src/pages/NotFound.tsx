import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { PageTransition } from "@/components/layout/PageTransition";
import { Button } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <PageTransition>
      <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
        <div className="mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-primary/10 text-primary">
          <Compass size={30} />
        </div>
        <p className="font-display text-6xl text-foreground">404</p>
        <p className="mt-2 text-lg text-foreground">Page not found</p>
        <p className="mt-1 max-w-sm text-sm text-muted">
          The page you're looking for doesn't exist or has moved.
        </p>
        <Link to="/" className="mt-6">
          <Button>Back to Dashboard</Button>
        </Link>
      </div>
    </PageTransition>
  );
}
