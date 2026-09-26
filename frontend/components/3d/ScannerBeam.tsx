'use client';

import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface ScannerBeamProps {
  position?: [number, number, number];
  rotation?: [number, number, number];
  active?: boolean;
}

export function ScannerBeam({
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  active = true,
}: ScannerBeamProps) {
  const ringRef = useRef<THREE.Mesh>(null);
  const beamRef = useRef<THREE.Mesh>(null);
  const matRef = useRef<THREE.MeshBasicMaterial>(null);

  useFrame((state) => {
    if (!ringRef.current) return;
    const t = state.clock.elapsedTime;
    ringRef.current.rotation.z = t * 0.5;
    if (matRef.current) {
      matRef.current.opacity = active ? 0.15 + Math.sin(t * 3) * 0.08 : 0;
    }
    if (beamRef.current) {
      const bm = beamRef.current.material as THREE.MeshBasicMaterial;
      bm.opacity = active ? 0.25 + Math.sin(t * 4) * 0.1 : 0;
    }
  });

  if (!active) return null;

  return (
    <group position={position} rotation={rotation}>
      <mesh ref={ringRef}>
        <ringGeometry args={[1, 5, 64, 1]} />
        <meshBasicMaterial
          ref={matRef}
          color="#FACC15"
          transparent
          opacity={0.2}
          side={THREE.DoubleSide}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
      <mesh ref={beamRef} rotation={[0, 0, Math.PI / 4]}>
        <planeGeometry args={[10, 0.03]} />
        <meshBasicMaterial
          color="#FACC15"
          transparent
          opacity={0.3}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}
