"use client";

// React imports removed - not needed
import { Badge } from "@/components/ui/badge";

export type HighlightCategory = "Goal" | "Method" | "Result";

export interface Highlight {
  id: string;
  category: HighlightCategory;
  rect: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  pageNumber: number;
  text: string;
  metadata?: {
    confidence?: number;
    evidenceType?: string;
    section?: string;
    supportingEvidence?: string;
    methodologyContext?: string;
    studyPopulation?: string;
    limitations?: string;
    surroundingContext?: string;
  };
}

interface HighlightOverlayProps {
  highlights: Highlight[];
  currentPage: number;
  opacity: number;
  enabled: boolean;
  scale: number;
}

export function HighlightOverlay({
  highlights,
  currentPage,
  opacity,
  enabled,
  scale,
}: HighlightOverlayProps) {
  const pageHighlights = highlights.filter((highlight) => highlight.pageNumber === currentPage);

  if (!enabled) return null;

  const getCategoryColor = (category: HighlightCategory) => {
    switch (category) {
      case "Goal":
        return "bg-blue-500";
      case "Method":
        return "bg-amber-500";
      case "Result":
        return "bg-rose-500";
      default:
        return "bg-gray-500";
    }
  };

  const getCategoryTextColor = (category: HighlightCategory) => {
    switch (category) {
      case "Goal":
        return "text-blue-500";
      case "Method":
        return "text-amber-500";
      case "Result":
        return "text-rose-500";
      default:
        return "text-gray-500";
    }
  };

  return (
    <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
      {pageHighlights.map((highlight) => (
        <div
          key={highlight.id}
          className="absolute"
          style={{
            left: highlight.rect.x * scale,
            top: highlight.rect.y * scale,
            width: highlight.rect.width * scale,
            height: highlight.rect.height * scale,
          }}
        >
          <div
            className={`${getCategoryColor(highlight.category)} w-full h-full rounded-sm`}
            style={{ opacity: opacity }}
          />
          <Badge
            className={`absolute -top-6 left-0 pointer-events-auto ${getCategoryTextColor(
              highlight.category
            )}`}
            variant="outline"
          >
            {highlight.category}
          </Badge>
        </div>
      ))}
    </div>
  );
}
