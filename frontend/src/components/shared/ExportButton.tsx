"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Download, FileText, Table, FileSpreadsheet, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface ExportButtonProps {
  onExportPDF?: () => Promise<Blob | void>;
  onExportCSV?: () => string | Promise<string>;
  onExportExcel?: () => Promise<Blob | void>;
  disabled?: boolean;
  className?: string;
  fileName?: string;
}

export default function ExportButton({
  onExportPDF,
  onExportCSV,
  onExportExcel,
  disabled,
  className,
  fileName = "export",
}: ExportButtonProps) {
  const [isExporting, setIsExporting] = useState(false);

  const downloadBlob = (blob: Blob, name: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const runExport = async (fn: () => Promise<Blob | void> | string | Promise<string>, label: string, filename: string) => {
    setIsExporting(true);
    try {
      const result = await fn();
      if (result instanceof Blob) {
        downloadBlob(result, filename);
      } else if (typeof result === "string") {
        const blob = new Blob([result], { type: "text/csv;charset=utf-8;" });
        downloadBlob(blob, filename);
      }
      toast.success(`${label} exported successfully`);
    } catch {
      toast.error(`Failed to export ${label}`);
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportPDF = () => onExportPDF && runExport(onExportPDF, "PDF", `${fileName}.pdf`);
  const handleExportCSV = () => onExportCSV && runExport(onExportCSV, "CSV", `${fileName}.csv`);
  const handleExportExcel = () => onExportExcel && runExport(onExportExcel, "Excel", `${fileName}.xlsx`);

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
        {onExportExcel && (
          <DropdownMenuItem onClick={handleExportExcel}>
            <FileSpreadsheet className="mr-2 h-4 w-4" />
            Export as Excel (.xlsx)
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
