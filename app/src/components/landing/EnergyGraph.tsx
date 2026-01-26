'use client';

import React, { useEffect, useRef } from 'react';
import { theme } from '@/theme';

interface Candle {
    open: number;
    high: number;
    low: number;
    close: number;
    x: number;
}

export default function EnergyGraph() {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let animationFrameId: number;
        let scrollOffset = 0;
        const candleWidth = 12;
        const candleGap = 8;
        const totalCandleSpace = candleWidth + candleGap;

        // Data state
        let candles: Candle[] = [];

        const generateInitialData = (width: number, height: number) => {
            const count = Math.ceil(width / totalCandleSpace) + 5; // Extra buffer
            const data: Candle[] = [];
            let prevClose = height / 2;

            for (let i = 0; i < count; i++) {
                const change = (Math.random() - 0.5) * (height * 0.15); // Volatility
                let open = prevClose;
                let close = open + change;

                // Keep within bounds
                if (close < height * 0.2) close = height * 0.2 + Math.abs(change);
                if (close > height * 0.8) close = height * 0.8 - Math.abs(change);

                const high = Math.max(open, close) + Math.random() * (height * 0.05);
                const low = Math.min(open, close) - Math.random() * (height * 0.05);

                data.push({
                    open,
                    high,
                    low,
                    close,
                    x: i * totalCandleSpace
                });
                prevClose = close;
            }
            return data;
        };

        const updateData = (width: number, height: number) => {
            // Remove candles that have scrolled off screen
            if (candles.length > 0 && candles[0].x - scrollOffset < -totalCandleSpace) {
                candles.shift();

                // Add new candle at the end
                const lastCandle = candles[candles.length - 1];
                const change = (Math.random() - 0.5) * (height * 0.15);
                let open = lastCandle.close;
                let close = open + change;

                // Keep within bounds
                if (close < height * 0.2) close = height * 0.2 + Math.abs(change);
                if (close > height * 0.8) close = height * 0.8 - Math.abs(change);

                const high = Math.max(open, close) + Math.random() * (height * 0.05);
                const low = Math.min(open, close) - Math.random() * (height * 0.05);

                candles.push({
                    open,
                    high,
                    low,
                    close,
                    x: lastCandle.x + totalCandleSpace
                });

                // Adjust scroll offset to keep coordinate system consistent basically
                // Actually, simpler to just shift all x values? 
                // Let's stick to global scrollOffset for smooth animation, 
                // but resetting it periodically or shifting x is better for infinite scroll.
                // Approach: specific shift.
                candles.forEach(c => c.x -= totalCandleSpace);
                scrollOffset -= totalCandleSpace;
            }
        };

        const resize = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            candles = generateInitialData(canvas.width, canvas.height);
        };

        window.addEventListener('resize', resize);
        resize();

        const draw = () => {
            if (!ctx || !canvas) return;

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Update Logic
            scrollOffset += 0.5; // Scroll speed
            updateData(canvas.width, canvas.height);

            // Drawing
            candles.forEach(candle => {
                const drawX = candle.x - scrollOffset;

                // Skip if off-screen (optimization)
                if (drawX < -totalCandleSpace || drawX > canvas.width) return;

                const isUp = candle.close < candle.open; // Canvas Y axis is inverted (0 at top)
                // Note: In financial charts, Open < Close is UP. 
                // In Canvas Y: 0 is top. So lower Y value means higher "physical" position.
                // If Close (Y=100) < Open (Y=200), the price went UP visually.

                const color = isUp ? theme.colors.primary.orange : '#FFFFFF';
                // Glow settings
                ctx.shadowBlur = 15;
                ctx.shadowColor = color;
                ctx.fillStyle = color;
                ctx.strokeStyle = color;
                ctx.lineWidth = 2;

                // Draw Wick (High to Low)
                ctx.beginPath();
                ctx.moveTo(drawX + candleWidth / 2, candle.high);
                ctx.lineTo(drawX + candleWidth / 2, candle.low);
                ctx.stroke();

                // Draw Body (Open to Close)
                const bodyTop = Math.min(candle.open, candle.close);
                const bodyHeight = Math.abs(candle.close - candle.open);
                // Ensure minimal height for visibility
                const visualHeight = Math.max(bodyHeight, 2);

                ctx.fillRect(drawX, bodyTop, candleWidth, visualHeight);
            });

            animationFrameId = requestAnimationFrame(draw);
        };

        draw();

        return () => {
            window.removeEventListener('resize', resize);
            cancelAnimationFrame(animationFrameId);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className="absolute inset-0 z-0 pointer-events-none opacity-40 mix-blend-screen"
        />
    );
}
