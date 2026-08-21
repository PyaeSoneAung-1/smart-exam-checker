"use client";

import { useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Upload, File, X, AlertCircle, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  maxSizeMB?: number;
  className?: string;
}

export default function FileUpload({
  onFilesSelected,
  accept = ".pdf,.png,.jpg,.jpeg,.csv,.xlsx",
  multiple = false,
  maxSizeMB = 10,
  className,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const maxSizeBytes = maxSizeMB * 1024 * 1024;

  const validateAndAdd = useCallback(
    (newFiles: FileList | File[]) => {
      setError(null);
      const valid: File[] = [];
      const arr = Array.from(newFiles);

      for (const f of arr) {
        if (f.size > maxSizeBytes) {
          setError(`"${f.name}" exceeds ${maxSizeMB}MB limit`);
          continue;
        }
        valid.push(f);
      }

      if (valid.length) {
        const updated = multiple ? [...files, ...valid] : valid;
        setFiles(updated);
        onFilesSelected(updated);
      }
    },
    [files, multiple, maxSizeBytes, maxSizeMB, onFilesSelected]
  );

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length) validateAndAdd(e.dataTransfer.files);
  };

  const handleRemove = (idx: number) => {
    const updated = files.filter((_, i) => i !== idx);
    setFiles(updated);
    onFilesSelected(updated);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  return (
    <div className={cn("space-y-3", className)}>
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-8 cursor-pointer transition-colors",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50"
        )}
      >
        <Upload className={cn("h-10 w-10", isDragging ? "text-primary" : "text-muted-foreground")} />
        <div className="text-center">
          <p className="text-sm font-medium">
            {isDragging ? "Drop files here" : "Drag & drop files or click to browse"}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            {accept.replace(/\./g, "").toUpperCase().split(",").join(", ")} up to {maxSizeMB}MB
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) validateAndAdd(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((f, i) => (
            <div key={`${f.name}-${i}`} className="flex items-center gap-3 rounded-lg border p-3">
              <File className="h-4 w-4 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm truncate">{f.name}</p>
                <p className="text-xs text-muted-foreground">{formatSize(f.size)}</p>
              </div>
              <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={() => handleRemove(i)}>
                <X className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
