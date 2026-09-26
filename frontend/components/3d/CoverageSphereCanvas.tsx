'use client';

import { Canvas } from '@react-three/fiber';
import { Suspense } from 'react';
import { CoverageSphere } from './CoverageSphere';

export function CoverageSphereCanvas({
  coverage = 0.95,
}: {
  coverage?: number;
}) {
  return (
    <Canvas camera={{ position: [0, 0, 4], fov: 50 }} dpr={[1, 1.5]}>
      <Suspense fallback={null}>
        <ambientLight intensity={0.5} />
        <pointLight position={[3, 3, 3]} intensity={0.4} color="#FACC15" />
        <CoverageSphere coverage={coverage} />
      </Suspense>
    </Canvas>
  );
}
