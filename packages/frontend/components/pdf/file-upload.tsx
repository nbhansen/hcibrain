"use client";

import { AlertCircle, FileText, Upload, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  onUploadProgress?: (progress: { loaded: number; total: number }) => void;
  isUploading?: boolean;
  uploadProgress?: number;
  error?: string;
  maxSizeMB?: number;
}

export function FileUpload({
  onFileSelect,
  onUploadProgress: _onUploadProgress,
  isUploading = false,
  uploadProgress = 0,
  error,
  maxSizeMB = 50,
}: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback(
    (file: File): string | null => {
      // Check file type
      if (file.type !== "application/pdf") {
        return "Please select a PDF file";
      }

      // Check file size
      const sizeMB = file.size / (1024 * 1024);
      if (sizeMB > maxSizeMB) {
        return `File size must be less than ${maxSizeMB}MB (current: ${sizeMB.toFixed(1)}MB)`;
      }

      return null;
    },
    [maxSizeMB]
  );

  const handleFileSelection = useCallback(
    (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        // You could show a toast or set error state here
        console.error("File validation failed:", validationError);
        return;
      }

      setSelectedFile(file);
      onFileSelect(file);
    },
    [validateFile, onFileSelect]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        handleFileSelection(files[0]);
      }
    },
    [handleFileSelection]
  );

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleFileSelection(files[0]);
      }
    },
    [handleFileSelection]
  );

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const formatFileSize = (bytes: number): string => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Upload PDF
        </CardTitle>
        <CardDescription>
          Upload a research paper to extract key highlights (Goal, Method, Result)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {!selectedFile ? (
          // Upload area
          <div
            className={`
              border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer
              ${
                isDragOver
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50"
              }
              ${isUploading ? "pointer-events-none opacity-50" : ""}
            `}
            role="button"
            tabIndex={0}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleBrowseClick}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                handleBrowseClick();
              }
            }}
          >
            <div className="flex flex-col items-center gap-3">
              <div className="p-3 bg-muted rounded-full">
                <FileText className="h-8 w-8 text-muted-foreground" />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium">
                  {isDragOver ? "Drop your PDF here" : "Drag & drop your PDF here"}
                </p>
                <p className="text-xs text-muted-foreground">or click to browse files</p>
              </div>
              <p className="text-xs text-muted-foreground">Maximum file size: {maxSizeMB} MB</p>
            </div>
          </div>
        ) : (
          // Selected file display
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded">
                  <FileText className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{selectedFile.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatFileSize(selectedFile.size)}
                  </p>
                </div>
              </div>
              {!isUploading && (
                <Button variant="ghost" size="icon" onClick={handleClearFile} className="h-8 w-8">
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>

            {isUploading && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Processing...</span>
                  <span>{Math.round(uploadProgress)}%</span>
                </div>
                <Progress value={uploadProgress} className="h-2" />
              </div>
            )}
          </div>
        )}

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileInputChange}
          className="hidden"
        />
      </CardContent>
    </Card>
  );
}
