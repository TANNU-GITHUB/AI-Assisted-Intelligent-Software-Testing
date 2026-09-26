'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface BugObjectProps {
  position?: [number, number, number];
  scale?: number;
  detected?: boolean;
  speed?: number;
  color?: string;
}

export function BugObject({
  position = [0, 0, 0],
  scale = 1,
  detected = false,
  speed = 1,
  color = '#1a1a1a',
}: BugObjectProps) {
  const groupRef = useRef<THREE.Group>(null);
  const innerRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!groupRef.current) return;
    const t = state.clock.elapsedTime * speed;
    groupRef.current.position.y = position[1] + Math.sin(t * 0.8) * 0.2;
    groupRef.current.rotation.y = t * 0.3;

    if (innerRef.current) {
      const mat = innerRef.current.material as THREE.MeshStandardMaterial;
      if (detected) {
        mat.color.lerp(new THREE.Color('#EF4444'), 0.05);
        mat.emissive.lerp(new THREE.Color('#EF4444'), 0.05);
      } else {
        mat.emissive.lerp(new THREE.Color('#000000'), 0.05);
      }
    }
  });

  return (
    <group ref={groupRef} position={position} scale={scale}>
      {/* Core body - fragmented icosahedron */}
      <mesh ref={innerRef} castShadow>
        <icosahedronGeometry args={[0.4, 0]} />
        <meshStandardMaterial
          color={color}
          roughness={0.4}
          metalness={0.8}
          emissive={detected ? '#EF4444' : '#000000'}
          emissiveIntensity={detected ? 0.5 : 0}
          flatShading
        />
      </mesh>

      {/* Spikes */}
      {Array.from({ length: 6 }).map((_, i) => {
        const angle = (i / 6) * Math.PI * 2;
        return (
          <mesh
            key={i}
            position={[Math.cos(angle) * 0.4, 0, Math.sin(angle) * 0.4]}
            rotation={[0, angle, Math.PI / 2]}
          >
            <coneGeometry args={[0.06, 0.3, 4]} />
            <meshStandardMaterial
              color={detected ? '#EF4444' : '#222'}
              roughness={0.3}
              metalness={0.9}
            />
          </mesh>
        );
      })}

      {/* Glowing eyes */}
      <mesh position={[0.15, 0.1, 0.3]}>
        <sphereGeometry args={[0.04, 8, 8]} />
        <meshBasicMaterial color={detected ? '#FF0000' : '#FACC15'} />
      </mesh>
      <mesh position={[-0.15, 0.1, 0.3]}>
        <sphereGeometry args={[0.04, 8, 8]} />
        <meshBasicMaterial color={detected ? '#FF0000' : '#FACC15'} />
      </mesh>

      {/* Detection ring */}
      {detected && (
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.6, 0.7, 32]} />
          <meshBasicMaterial color="#FACC15" side={THREE.DoubleSide} transparent opacity={0.6} />
        </mesh>
      )}
    </group>
  );
}
