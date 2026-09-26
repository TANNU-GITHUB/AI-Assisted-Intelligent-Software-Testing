'use client';

import { Canvas } from '@react-three/fiber';
import { Suspense } from 'react';
import { BugObject } from './BugObject';

export function BugScanCanvas({
  detected = false,
  speed = 0.5,
}: {
  detected?: boolean;
  speed?: number;
}) {
  return (
    <Canvas camera={{ position: [0, 0, 4], fov: 50 }} dpr={[1, 1.5]}>
      <Suspense fallback={null}>
        <ambientLight intensity={0.3} />
        <pointLight position={[3, 3, 3]} intensity={0.4} color="#FACC15" />
        <BugObject detected={detected} speed={speed} scale={1.5} />
      </Suspense>
    </Canvas>
  );
}
