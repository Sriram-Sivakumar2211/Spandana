import { BookOpen } from "lucide-react";
import { Card } from "@/components/ui/Card";
import type { KnowledgeChunk } from "@/types";

/**
 * Surfaces the actual knowledge-base chunks the RAG retriever matched
 * (genai/retrieval.py's TF-IDF + cosine-similarity search) for the query it
 * built from this prediction -- evidence the report below is grounded in
 * real documents, not an ungrounded LLM guess.
 */
export function KnowledgeSourcesCard({ query, chunks }: { query: string; chunks: KnowledgeChunk[] }) {
  if (chunks.length === 0) return null;
  return (
    <Card className="p-5">
      <div className="mb-1 flex items-center gap-2 text-foreground">
        <BookOpen size={16} className="text-primary" />
        <h3 className="font-display text-lg">Retrieved Knowledge Sources</h3>
      </div>
      <p className="mb-3 text-xs text-muted">
        Query: <span className="tnum text-foreground">{query}</span>
      </p>
      <ul className="space-y-2">
        {chunks.map((c) => (
          <li key={c.chunk_id} className="rounded-xl border border-border bg-background/50 p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium text-foreground">{c.title}</p>
              <span className="shrink-0 text-[11px] text-muted tnum">
                score {c.relevance_score.toFixed(3)}
              </span>
            </div>
            <p className="mt-1 text-xs text-muted">{c.source_file}</p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
