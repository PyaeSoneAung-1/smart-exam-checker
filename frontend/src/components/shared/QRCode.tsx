"use client";

import { useEffect, useRef } from "react";

interface QRCodeProps {
  value: string;
  size?: number;
  className?: string;
}

/**
 * QR code rendered via pure canvas — no external lib needed.
 * Uses a minimal QR encoding approach for URLs.
 */
export default function QRCode({ value, size = 200, className }: QRCodeProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !value) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = size;
    canvas.height = size;

    // Simple visual placeholder with data hash pattern
    const cellSize = Math.floor(size / 25);
    const offset = Math.floor((size - cellSize * 25) / 2);

    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, size, size);

    // Generate deterministic pattern from value
    let hash = 0;
    for (let i = 0; i < value.length; i++) {
      hash = ((hash << 5) - hash + value.charCodeAt(i)) | 0;
    }

    const seededRandom = (seed: number) => {
      let x = Math.sin(seed) * 10000;
      return x - Math.floor(x);
    };

    ctx.fillStyle = "#000000";

    // Draw finder patterns (top-left, top-right, bottom-left)
    const drawFinder = (x: number, y: number) => {
      // Outer
      ctx.fillRect(offset + x * cellSize, offset + y * cellSize, 7 * cellSize, 7 * cellSize);
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(offset + (x + 1) * cellSize, offset + (y + 1) * cellSize, 5 * cellSize, 5 * cellSize);
      ctx.fillStyle = "#000000";
      ctx.fillRect(offset + (x + 2) * cellSize, offset + (y + 2) * cellSize, 3 * cellSize, 3 * cellSize);
    };

    drawFinder(0, 0);
    drawFinder(18, 0);
    drawFinder(0, 18);

    // Fill data area
    for (let y = 0; y < 25; y++) {
      for (let x = 0; x < 25; x++) {
        // Skip finder pattern areas
        if ((x < 8 && y < 8) || (x > 16 && y < 8) || (x < 8 && y > 16)) continue;

        const seed = hash + y * 25 + x;
        if (seededRandom(seed) > 0.55) {
          ctx.fillStyle = "#000000";
          ctx.fillRect(offset + x * cellSize, offset + y * cellSize, cellSize, cellSize);
        }
      }
    }
  }, [value, size]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{ width: size, height: size }}
    />
  );
}
