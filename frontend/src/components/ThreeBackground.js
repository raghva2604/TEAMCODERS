import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import { useRef } from "react";

function FloatingSphere() {
  const ref = useRef();
  useFrame(() => {
    if (ref.current) {
      ref.current.rotation.y += 0.0015;
      ref.current.rotation.x += 0.0008;
    }
  });
  return (
    <mesh ref={ref} position={[0, 0, 0]}>
      <sphereGeometry args={[2.4, 64, 64]} />
      <meshStandardMaterial color="#00ffff" wireframe opacity={0.45} transparent />
    </mesh>
  );
}

function FloatingRing({ position, color }) {
  const ref = useRef();
  useFrame(() => {
    if (ref.current) {
      ref.current.rotation.z += 0.0025;
      ref.current.rotation.x += 0.0012;
    }
  });
  return (
    <mesh ref={ref} position={position} rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[1.5, 0.08, 16, 100]} />
      <meshStandardMaterial color={color} transparent opacity={0.18} />
    </mesh>
  );
}

function FloatingBox({ position, color }) {
  const ref = useRef();
  useFrame(() => {
    if (ref.current) {
      ref.current.rotation.y += 0.003;
      ref.current.rotation.x += 0.002;
    }
  });
  return (
    <mesh ref={ref} position={position}>
      <boxGeometry args={[1.1, 1.1, 1.1]} />
      <meshStandardMaterial color={color} roughness={0.25} metalness={0.7} opacity={0.3} transparent />
    </mesh>
  );
}

export default function ThreeBackground() {
  return (
    <div className="three-background">
      <Canvas camera={{ position: [0, 0, 14], fov: 55 }}>
        <fog attach="fog" args={["#020511", 10, 35]} />
        <ambientLight intensity={0.45} />
        <directionalLight position={[8, 8, 5]} intensity={0.8} />
        <FloatingSphere />
        <FloatingRing position={[-4, 2, -2]} color="#6bc8ff" />
        <FloatingRing position={[4, -1, -1]} color="#9e7dff" />
        <FloatingBox position={[-3.2, -2.2, -4]} color="#00ffff" />
        <FloatingBox position={[3.5, 2.0, -3]} color="#ff8cff" />
        <Stars radius={80} depth={25} count={3000} factor={8} saturation={0} fade />
        <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.08} />
      </Canvas>
    </div>
  );
}
