'use client';

import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface BrowserObjectProps {
  position?: [number, number, number];
  scale?: number;
  active?: boolean;
}

export function BrowserObject({
  position = [0, 0, 0],
  scale = 1,
  active = false,
}: BrowserObjectProps) {
  const groupRef = useRef<THREE.Group>(null);
  const screenRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!groupRef.current) return;
    const t = state.clock.elapsedTime;
    groupRef.current.position.y = position[1] + Math.sin(t * 0.5) * 0.1;
    groupRef.current.rotation.y = Math.sin(t * 0.2) * 0.1;

    if (screenRef.current) {
      const mat = screenRef.current.material as THREE.MeshBasicMaterial;
      mat.opacity = active ? 0.8 : 0.3;
    }
  });

  return (
    <group ref={groupRef} position={position} scale={scale}>
      {/* Frame */}
      <mesh>
        <boxGeometry args={[1.5, 1, 0.08]} />
        <meshStandardMaterial color="#171717" roughness={0.4} metalness={0.8} />
      </mesh>
      {/* Screen */}
      <mesh ref={screenRef} position={[0, 0, 0.041]}>
        <planeGeometry args={[1.4, 0.9]} />
        <meshBasicMaterial color={active ? '#FACC15' : '#0a0a0a'} transparent opacity={0.3} />
      </mesh>
      {/* Top bar */}
      <mesh position={[0, 0.4, 0.042]}>
        <planeGeometry args={[1.4, 0.08]} />
        <meshBasicMaterial color="#262626" />
      </mesh>
      {/* Dots */}
      {[-0.6, -0.55, -0.5].map((x, i) => (
        <mesh key={i} position={[x, 0.4, 0.043]}>
          <circleGeometry args={[0.015, 8]} />
          <meshBasicMaterial color={i === 0 ? '#EF4444' : i === 1 ? '#FACC15' : '#22C55E'} />
        </mesh>
      ))}
      {/* Content lines */}
      {Array.from({ length: 4 }).map((_, i) => (
        <mesh key={i} position={[-0.3, 0.2 - i * 0.15, 0.043]}>
          <planeGeometry args={[0.8, 0.04]} />
          <meshBasicMaterial color="#FACC15" transparent opacity={active ? 0.4 : 0.15} />
        </mesh>
      ))}
    </group>
  );
}
