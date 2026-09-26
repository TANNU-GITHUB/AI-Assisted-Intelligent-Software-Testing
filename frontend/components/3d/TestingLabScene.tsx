'use client';

import { Suspense, useRef, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { TestingCore } from './TestingCore';
import { ParticleField } from './ParticleField';
import { BugObject } from './BugObject';
import { BrowserObject } from './BrowserObject';
import { ScannerBeam } from './ScannerBeam';

function MouseCamera() {
  const { camera, pointer } = useThree();

  useFrame(() => {
    camera.position.x += (pointer.x * 2 - camera.position.x) * 0.03;
    camera.position.y += (pointer.y * 1 + 1 - camera.position.y) * 0.03;
    camera.lookAt(0, 0, 0);
  });

  return null;
}

interface TestingLabSceneProps {
  scrollProgress?: number;
  className?: string;
}

export function TestingLabScene({
  scrollProgress = 0,
  className,
}: TestingLabSceneProps) {
  return (
    <div className={className} style={{ width: '100%', height: '100%' }}>
      <Canvas
        camera={{ position: [0, 1, 8], fov: 50 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true }}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.3} />
          <pointLight position={[5, 5, 5]} intensity={0.5} color="#FACC15" />
          <pointLight position={[-5, -5, -5]} intensity={0.3} color="#FACC15" />
          <spotLight position={[0, 10, 0]} angle={0.3} penumbra={1} intensity={0.5} color="#FACC15" />

          <MouseCamera />

          <TestingCore scrollProgress={scrollProgress} />

          <ParticleField count={150} radius={7} size={0.04} />

          {/* Orbiting browsers */}
          <BrowserObject position={[4, 1, -2]} scale={0.8} />
          <BrowserObject position={[-4, -1, -1]} scale={0.6} />
          <BrowserObject position={[3, -2, 2]} scale={0.5} active />

          {/* Bugs */}
          <BugObject position={[3, 2, 1]} scale={0.6} speed={0.8} />
          <BugObject position={[-3, 1.5, -2]} scale={0.5} speed={1.2} />
          <BugObject position={[2, -2.5, 0]} scale={0.4} speed={0.6} detected />

          {/* Scanner */}
          <ScannerBeam position={[0, 0, 0]} active={scrollProgress > 0.1} />

          <OrbitControls
            enableZoom={false}
            enablePan={false}
            autoRotate
            autoRotateSpeed={0.3}
            minPolarAngle={Math.PI / 3}
            maxPolarAngle={Math.PI / 1.8}
          />
        </Suspense>
      </Canvas>
    </div>
  );
}
