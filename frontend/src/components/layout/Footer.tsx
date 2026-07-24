export function Footer() {
  return (
    <footer className="border-t border-border px-6 py-4">
      <div className="flex flex-col items-center justify-between gap-2 text-xs text-muted sm:flex-row">
        <p>
          © {new Date().getFullYear()} SPANDANA · AI Powered Predictive
          Maintenance
        </p>
        <p className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
          Powered by Liquid Time-Constant Networks (ncps)
        </p>
      </div>
    </footer>
  );
}
