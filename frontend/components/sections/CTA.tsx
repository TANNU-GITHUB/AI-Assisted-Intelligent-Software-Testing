'use client';

import { motion } from 'motion/react';
import Link from 'next/link';
import { LabButton } from '@/components/ui/LabButton';
import { ArrowRight, Bug } from 'lucide-react';

export function CTA() {
  return (
    <section className="relative py-24 sm:py-32 px-6 sm:px-10 lg:px-20 overflow-hidden">
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-[600px] h-[600px] rounded-full bg-yellow-500/5 blur-3xl" />
      </div>

      <div className="relative max-w-3xl mx-auto text-center">
        {/* Bug icon */}
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          whileInView={{ scale: 1, rotate: 0 }}
          viewport={{ once: true }}
          transition={{ type: 'spring', stiffness: 200, damping: 15 }}
          className="inline-flex items-center justify-center w-16 h-16 rounded-2xl border border-yellow-500/30 bg-yellow-500/10 mb-8"
        >
          <Bug className="w-8 h-8 text-yellow-500" />
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground tracking-tight text-balance"
        >
          Stop Shipping Bugs.
          <br />
          <span className="text-yellow-500">Start Testing Smarter.</span>
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mt-6 text-muted-foreground text-base sm:text-lg max-w-xl mx-auto"
        >
          Experience the AI testing laboratory. Generate test cases, execute
          them, and catch defects before they reach your users.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-10 flex flex-col sm:flex-row gap-4 justify-center"
        >
          <Link href="/live-lab">
            <LabButton size="lg">
              Launch The Lab
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </LabButton>
          </Link>
          <Link href="/dashboard">
            <LabButton variant="secondary" size="lg">
              View Dashboard
            </LabButton>
          </Link>
        </motion.div>
      </div>
    </section>
  );
}
