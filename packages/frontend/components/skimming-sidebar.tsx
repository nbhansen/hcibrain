"use client";

import { X } from "lucide-react";
// useState not used in this component
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";

interface SkimmingSidebarProps {
  enabled: boolean;
  setEnabled: (enabled: boolean) => void;
  opacity: number;
  setOpacity: (opacity: number) => void;
  highlightCount: number;
  setHighlightCount: (count: number) => void;
  totalHighlights?: number;
  extractionSummary?: {
    paper: {
      title: string;
      authors: string[];
      paperId: string;
    };
    summary: {
      totalElements: number;
      elementsByType: Record<string, number>;
      elementsBySection: Record<string, number>;
      averageConfidence: number;
      processingTime: number;
      createdAt: string;
      paperSummary?: string;
      paperSummaryConfidence?: number;
    };
  } | null;
  onNewUpload?: () => void;
  onClose?: () => void;
  confidenceThreshold?: number;
  setConfidenceThreshold?: (threshold: number) => void;
  highlightsAboveThreshold?: number;
}

export function SkimmingSidebar({
  enabled,
  setEnabled,
  opacity,
  setOpacity,
  highlightCount,
  setHighlightCount,
  totalHighlights = 0,
  extractionSummary,
  onNewUpload,
  onClose,
  confidenceThreshold = 0.5,
  setConfidenceThreshold,
  highlightsAboveThreshold = totalHighlights,
}: SkimmingSidebarProps) {
  return (
    <Card className="w-full max-w-xs">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg">Skimming Highlights</CardTitle>
        {onClose && (
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between">
          <Label htmlFor="highlights-toggle" className="font-medium">
            Enable Highlights
          </Label>
          <Switch id="highlights-toggle" checked={enabled} onCheckedChange={setEnabled} />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="opacity-slider" className="font-medium">
              Highlight Opacity
            </Label>
            <span className="text-sm text-muted-foreground">{Math.round(opacity * 100)}%</span>
          </div>
          <Slider
            id="opacity-slider"
            min={0.1}
            max={1}
            step={0.05}
            value={[opacity]}
            onValueChange={(values) => setOpacity(values[0])}
            disabled={!enabled}
          />
        </div>

        {setConfidenceThreshold && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="confidence-slider" className="font-medium">
                Confidence Threshold
              </Label>
              <span className="text-sm text-muted-foreground">
                {Math.round(confidenceThreshold * 100)}%
              </span>
            </div>
            <Slider
              id="confidence-slider"
              min={0}
              max={1}
              step={0.05}
              value={[confidenceThreshold]}
              onValueChange={(values) => setConfidenceThreshold(values[0])}
              disabled={!enabled}
            />
            <p className="text-xs text-muted-foreground">
              {highlightsAboveThreshold} of {totalHighlights} highlights above threshold
            </p>
          </div>
        )}

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="highlight-count" className="font-medium">
              Number of Highlights
            </Label>
            <span className="text-sm text-muted-foreground">
              {highlightCount} of {highlightsAboveThreshold}
            </span>
          </div>
          <Input
            id="highlight-count"
            type="number"
            min={1}
            max={Math.max(highlightsAboveThreshold, 20)}
            value={highlightCount}
            onChange={(e) => setHighlightCount(Number(e.target.value))}
            disabled={!enabled}
          />
        </div>

        {onNewUpload && (
          <>
            <Separator />
            <Button variant="outline" onClick={onNewUpload} className="w-full">
              Upload New PDF
            </Button>
          </>
        )}

        <Separator />

        {extractionSummary && (
          <div className="space-y-3">
            <p className="font-medium">Extraction Summary</p>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Total Elements:</span>
                <span className="font-medium">{extractionSummary.summary?.totalElements || 0}</span>
              </div>
              <div className="flex justify-between">
                <span>Avg. Confidence:</span>
                <span className="font-medium">
                  {extractionSummary.summary?.averageConfidence
                    ? `${Math.round(extractionSummary.summary.averageConfidence * 100)}%`
                    : "N/A"}
                </span>
              </div>
              {extractionSummary.paper && (
                <div className="pt-2">
                  <p className="font-medium text-xs">Paper:</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {extractionSummary.paper.title}
                  </p>
                </div>
              )}
            </div>
            <Separator />
          </div>
        )}

        <div className="space-y-2">
          <p className="font-medium">Highlight Categories</p>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="text-blue-500">
              Goal
            </Badge>
            <Badge variant="outline" className="text-amber-500">
              Method
            </Badge>
            <Badge variant="outline" className="text-rose-500">
              Result
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
