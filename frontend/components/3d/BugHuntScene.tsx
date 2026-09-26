'use client';

import { Suspense, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { BugObject } from './BugObject';
import { ParticleField } from './ParticleField';

function MiniBrowser({ position, active }: { position: [number, number, number]; active: boolean }) {
  const ref = useRef<THREE.Group>(null);
  useFrame((state) => {
    if (!ref.current) return;
    ref.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 0.5 + position[0]) * 0.15;
    ref.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.2) * 0.15;
  });

  return (
    <group ref={ref} position={position}>
      <mesh>
        <boxGeometry args={[1.2, 0.8, 0.05]} />
        <meshStandardMaterial color="#171717" roughness={0.4} metalness={0.7} />
      </mesh>
      <mesh position={[0, 0, 0.03]}>
        <planeGeometry args={[1.1, 0.7]} />
        <meshBasicMaterial color={active ? '#FACC15' : '#0a0a0a'} transparent opacity={0.2} />
      </mesh>
    </group>
  );
}

function BugHuntContent({ active }: { active: boolean }) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.y = state.clock.elapsedTime * 0.1;
  });

  return (
    <group ref={groupRef}>
      <ambientLight intensity={0.3} />
      <pointLight position={[3, 3, 3]} intensity={0.4} color="#FACC15" />

      {/* Mini browsers */}
      <MiniBrowser position={[1.5, 0.5, 0]} active={active} />
      <MiniBrowser position={[-1.5, -0.3, 0.5]} active={false} />
      <MiniBrowser position={[0, 1.2, -1]} active={false} />

      {/* Hidden bug */}
      <BugObject position={[1.5, 0.5, 0.3]} scale={0.3} detected={active} speed={0.5} />

      {/* Particles */}
      <ParticleField count={50} radius={3} size={0.03} />
    </group>
  );
}

export function BugHuntScene({ active }: { active: boolean }) {
  return (
    <Canvas camera={{ position: [0, 0, 4], fov: 50 }} dpr={[1, 1.5]}>
      <Suspense fallback={null}>
        <BugHuntContent active={active} />
      </Suspense>
    </Canvas>
  );
}
