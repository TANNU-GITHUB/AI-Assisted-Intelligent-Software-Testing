'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface TestingCoreProps {
  scrollProgress?: number;
  active?: boolean;
}

export function TestingCore({ scrollProgress = 0, active = true }: TestingCoreProps) {
  const groupRef = useRef<THREE.Group>(null);
  const ring1Ref = useRef<THREE.Mesh>(null);
  const ring2Ref = useRef<THREE.Mesh>(null);
  const ring3Ref = useRef<THREE.Mesh>(null);
  const coreRef = useRef<THREE.Mesh>(null);

  const nodes = useMemo(() => {
    return Array.from({ length: 8 }).map((_, i) => {
      const angle = (i / 8) * Math.PI * 2;
      const r = 2.5;
      return {
        position: [
          Math.cos(angle) * r,
          Math.sin(angle * 2) * 0.5,
          Math.sin(angle) * r,
        ] as [number, number, number],
        angle,
      };
    });
  }, []);

  useFrame((state) => {
    if (!groupRef.current) return;
    const t = state.clock.elapsedTime;

    // Breathing
    const breathe = 1 + Math.sin(t * 0.8) * 0.03;
    groupRef.current.scale.setScalar(breathe);

    // Slow rotation
    groupRef.current.rotation.y = t * 0.1 + scrollProgress * Math.PI * 2;

    // Ring rotations
    if (ring1Ref.current) ring1Ref.current.rotation.z = t * 0.4;
    if (ring2Ref.current) {
      ring2Ref.current.rotation.x = t * 0.3;
      ring2Ref.current.rotation.y = t * 0.2;
    }
    if (ring3Ref.current) {
      ring3Ref.current.rotation.y = -t * 0.5;
      ring3Ref.current.rotation.z = t * 0.15;
    }

    // Core pulsing
    if (coreRef.current) {
      const mat = coreRef.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = active ? 0.3 + Math.sin(t * 2) * 0.15 : 0.1;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Central core */}
      <mesh ref={coreRef}>
        <icosahedronGeometry args={[1, 1]} />
        <meshStandardMaterial
          color="#0a0a0a"
          roughness={0.2}
          metalness={0.9}
          emissive="#FACC15"
          emissiveIntensity={0.3}
          flatShading
        />
      </mesh>

      {/* Inner wireframe */}
      <mesh scale={1.05}>
        <icosahedronGeometry args={[1, 1]} />
        <meshBasicMaterial color="#FACC15" wireframe transparent opacity={0.15} />
      </mesh>

      {/* Ring 1 - horizontal */}
      <mesh ref={ring1Ref} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[2.5, 0.02, 8, 64]} />
        <meshStandardMaterial color="#FACC15" emissive="#FACC15" emissiveIntensity={0.3} />
      </mesh>

      {/* Ring 2 - tilted */}
      <mesh ref={ring2Ref} rotation={[0.5, 0, 0.3]}>
        <torusGeometry args={[3, 0.015, 8, 64]} />
        <meshStandardMaterial color="#FACC15" emissive="#FACC15" emissiveIntensity={0.2} transparent opacity={0.7} />
      </mesh>

      {/* Ring 3 - vertical */}
      <mesh ref={ring3Ref} rotation={[0, 0, Math.PI / 4]}>
        <torusGeometry args={[3.5, 0.01, 8, 64]} />
        <meshStandardMaterial color="#FACC15" emissive="#FACC15" emissiveIntensity={0.15} transparent opacity={0.5} />
      </mesh>

      {/* Orbiting nodes */}
      {nodes.map((node, i) => (
        <OrbitingNode key={i} position={node.position} index={i} />
      ))}

      {/* Code fragments */}
      {Array.from({ length: 5 }).map((_, i) => (
        <CodeFragment key={i} index={i} />
      ))}
    </group>
  );
}

function OrbitingNode({ position, index }: { position: [number, number, number]; index: number }) {
  const ref = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.elapsedTime;
    ref.current.position.y = position[1] + Math.sin(t + index) * 0.3;
    ref.current.scale.setScalar(0.8 + Math.sin(t * 2 + index) * 0.2);
  });

  return (
    <mesh ref={ref} position={position}>
      <boxGeometry args={[0.15, 0.15, 0.15]} />
      <meshStandardMaterial
        color="#FACC15"
        emissive="#FACC15"
        emissiveIntensity={0.5}
        roughness={0.3}
        metalness={0.7}
      />
    </mesh>
  );
}

function CodeFragment({ index }: { index: number }) {
  const ref = useRef<THREE.Group>(null);
  const angle = (index / 5) * Math.PI * 2;
  const radius = 4;

  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.elapsedTime * 0.3;
    ref.current.position.x = Math.cos(angle + t) * radius;
    ref.current.position.z = Math.sin(angle + t) * radius;
    ref.current.position.y = Math.sin(t * 2 + index) * 1;
    ref.current.rotation.y = t + index;
  });

  return (
    <group ref={ref}>
      <mesh>
        <boxGeometry args={[0.3, 0.4, 0.02]} />
        <meshStandardMaterial color="#171717" emissive="#FACC15" emissiveIntensity={0.05} roughness={0.5} />
      </mesh>
      {/* Lines on the code block */}
      {Array.from({ length: 4 }).map((_, i) => (
        <mesh key={i} position={[0, 0.12 - i * 0.08, 0.011]}>
          <planeGeometry args={[0.2 - i * 0.03, 0.015]} />
          <meshBasicMaterial color="#FACC15" transparent opacity={0.3} />
        </mesh>
      ))}
    </group>
  );
}
