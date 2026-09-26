'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface TestNodeProps {
  position?: [number, number, number];
  status?: 'pending' | 'running' | 'passed' | 'failed';
  index?: number;
}

const statusColors = {
  pending: '#FACC15',
  running: '#FFD60A',
  passed: '#22C55E',
  failed: '#EF4444',
};

export function TestNode({
  position = [0, 0, 0],
  status = 'pending',
  index = 0,
}: TestNodeProps) {
  const ref = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.elapsedTime;
    ref.current.position.y = position[1] + Math.sin(t * 2 + index) * 0.05;
    ref.current.rotation.x = t * 0.5 + index;
    ref.current.rotation.y = t * 0.3 + index;
  });

  return (
    <mesh ref={ref} position={position}>
      <octahedronGeometry args={[0.08, 0]} />
      <meshStandardMaterial
        color={statusColors[status]}
        emissive={statusColors[status]}
        emissiveIntensity={0.4}
        roughness={0.3}
        metalness={0.6}
      />
    </mesh>
  );
}

export function TestNodeStream({ count = 30 }: { count?: number }) {
  const groupRef = useRef<THREE.Group>(null);

  const nodes = useMemo(() => {
    return Array.from({ length: count }).map((_, i) => ({
      position: [
        (Math.random() - 0.5) * 4,
        (Math.random() - 0.5) * 3,
        (Math.random() - 0.5) * 2,
      ] as [number, number, number],
      status: (['pending', 'passed', 'failed', 'running'] as const)[
        Math.floor(Math.random() * 4)
      ],
      index: i,
    }));
  }, [count]);

  useFrame((state) => {
    if (!groupRef.current) return;
    const t = state.clock.elapsedTime;
    groupRef.current.rotation.y = t * 0.05;
  });

  return (
    <group ref={groupRef}>
      {nodes.map((node, i) => (
        <TestNode key={i} {...node} />
      ))}
    </group>
  );
}
