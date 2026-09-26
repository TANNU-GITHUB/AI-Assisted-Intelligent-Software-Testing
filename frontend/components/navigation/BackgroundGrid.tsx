'use client';

import { useEffect, useRef } from 'react';
import { useTheme } from './ThemeProvider';

export function BackgroundGrid() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { theme } = useTheme();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const c = ctx;

    const prefersReduced = window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    ).matches;

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const isLight = theme === 'light';

    const particles: { x: number; y: number; vx: number; vy: number; size: number }[] = [];
    const count = prefersReduced ? 0 : Math.min(30, Math.floor(width / 50));
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        size: Math.random() * 1.5 + 0.5,
      });
    }

    let scanY = -100;
    let scanActive = false;
    let scanTimer = 0;

    const onResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', onResize);

    let rafId: number;
    function draw() {
      c.clearRect(0, 0, width, height);

      // Grid lines
      if (isLight) {
        c.strokeStyle = 'rgba(30,30,80,0.06)';
      } else {
        c.strokeStyle = 'rgba(255,255,255,0.025)';
      }
      c.lineWidth = 1;
      const gridSize = 40;
      for (let x = 0; x < width; x += gridSize) {
        c.beginPath();
        c.moveTo(x, 0);
        c.lineTo(x, height);
        c.stroke();
      }
      for (let y = 0; y < height; y += gridSize) {
        c.beginPath();
        c.moveTo(0, y);
        c.lineTo(width, y);
        c.stroke();
      }

      // Particles
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;
        // In light mode make particles golden-amber, slightly more opaque
        c.fillStyle = isLight ? 'rgba(202,138,4,0.35)' : 'rgba(250,204,21,0.3)';
        c.beginPath();
        c.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        c.fill();
      });

      // Scan beam
      scanTimer++;
      if (scanTimer > 600 && !scanActive) {
        scanActive = true;
        scanY = -50;
      }
      if (scanActive) {
        scanY += 3;
        const gradient = c.createLinearGradient(0, scanY - 40, 0, scanY + 40);
        if (isLight) {
          gradient.addColorStop(0, 'rgba(202,138,4,0)');
          gradient.addColorStop(0.5, 'rgba(202,138,4,0.09)');
          gradient.addColorStop(1, 'rgba(202,138,4,0)');
        } else {
          gradient.addColorStop(0, 'rgba(250,204,21,0)');
          gradient.addColorStop(0.5, 'rgba(250,204,21,0.06)');
          gradient.addColorStop(1, 'rgba(250,204,21,0)');
        }
        c.fillStyle = gradient;
        c.fillRect(0, scanY - 40, width, 80);
        if (scanY > height + 50) {
          scanActive = false;
          scanTimer = 0;
        }
      }

      rafId = requestAnimationFrame(draw);
    }
    draw();

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener('resize', onResize);
    };
  }, [theme]); // re-run when theme changes

  return (
    <canvas
      ref={canvasRef}
      className={`fixed inset-0 -z-10 pointer-events-none transition-all duration-500 ${
        theme === 'light' ? 'bg-[#f5f0e8]' : 'bg-[#080808]'
      }`}
    />
  );
}
