'use client';

import { useEffect, useState } from 'react';
import { motion, useMotionValue, useSpring } from 'motion/react';

export function CustomCursor() {
  const [variant, setVariant] = useState<'default' | 'hover' | 'scan' | 'open'>('default');
  const [visible, setVisible] = useState(false);
  const x = useMotionValue(-100);
  const y = useMotionValue(-100);
  const springX = useSpring(x, { stiffness: 500, damping: 40 });
  const springY = useSpring(y, { stiffness: 500, damping: 40 });

  useEffect(() => {
    const isTouch = window.matchMedia('(hover: none)').matches;
    if (isTouch) return;

    const onMove = (e: MouseEvent) => {
      x.set(e.clientX);
      y.set(e.clientY);
      setVisible(true);

      const target = e.target as HTMLElement;
      if (target.closest('button, a, [role="button"]')) {
        setVariant('open');
      } else if (target.closest('[data-cursor="scan"]')) {
        setVariant('scan');
      } else if (target.closest('[data-cursor="hover"]')) {
        setVariant('hover');
      } else {
        setVariant('default');
      }
    };

    const onLeave = () => setVisible(false);

    window.addEventListener('mousemove', onMove);
    document.addEventListener('mouseleave', onLeave);
    return () => {
      window.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseleave', onLeave);
    };
  }, [x, y]);

  if (!visible) return null;

  const sizes = {
    default: 8,
    hover: 16,
    scan: 36,
    open: 40,
  };

  const labels: Record<string, string> = {
    scan: 'SCAN',
    open: 'OPEN',
  };

  const size = sizes[variant];

  return (
    <motion.div
      className="fixed top-0 left-0 z-[9999] pointer-events-none mix-blend-difference"
      style={{ x: springX, y: springY }}
    >
      <motion.div
        className="flex items-center justify-center rounded-full border border-yellow-500 -translate-x-1/2 -translate-y-1/2"
        animate={{
          width: size,
          height: size,
          backgroundColor: variant === 'default' ? 'rgba(250,204,21,1)' : 'rgba(250,204,21,0.1)',
        }}
        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      >
        {labels[variant] && (
          <span className="text-[8px] font-mono font-bold text-yellow-500">
            {labels[variant]}
          </span>
        )}
      </motion.div>
    </motion.div>
  );
}
