"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Download, FileText, Table, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface ExportButtonProps {
  onExportPDF?: () => Promise<Blob | void>;
  onExportCSV?: () => string | Promise<string>;
  disabled?: boolean;
  className?: string;
}

export default function ExportButton({
  onExportPDF,
  onExportCSV,
  disabled,
  className,
}: ExportButtonProps) {
  const [isExporting, setIsExporting] = useState(false);

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExportPDF = async () => {
    if (!onExportPDF) return;
    setIsExporting(true);
    try {
      const result = await onExportPDF();
      if (result instanceof Blob) {
        downloadBlob(result, "report.pdf");
        toast.success("PDF exported successfully");
      }
    } catch {
      toast.error("Failed to export PDF");
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportCSV = async () => {
    if (!onExportCSV) return;
    setIsExporting(true);
    try {
      const csv = await onExportCSV();
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      downloadBlob(blob, "export.csv");
      toast.success("CSV exported successfully");
    } catch {
      toast.error("Failed to export CSV");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn("inline-flex items-center justify-center", disabled || isExporting ? "opacity-50 pointer-events-none" : "")}
      >
        <Button variant="outline" disabled={disabled || isExporting} className={className}>
          {isExporting ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Download className="mr-2 h-4 w-4" />
          )}
          Export
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {onExportPDF && (
          <DropdownMenuItem onClick={handleExportPDF}>
            <FileText className="mr-2 h-4 w-4" />
            Export as PDF
          </DropdownMenuItem>
        )}
        {onExportCSV && (
          <DropdownMenuItem onClick={handleExportCSV}>
            <Table className="mr-2 h-4 w-4" />
            Export as CSV
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
