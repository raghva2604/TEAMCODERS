import { motion } from "framer-motion";

export default function Particles() {
  return (
    <div className="particle-background">
      {[...Array(32)].map((_, index) => {
        const size = 2 + Math.random() * 4;
        const left = Math.random() * 100;
        const delay = Math.random() * 5;
        const duration = 6 + Math.random() * 8;
        const color = Math.random() > 0.5 ? "rgba(0,255,255,0.4)" : "rgba(138,43,226,0.3)";

        return (
          <motion.span
            key={index}
            className="particle-dot"
            style={{ left: `${left}%`, width: size, height: size, background: color }}
            initial={{ y: 0, opacity: 0 }}
            animate={{ y: [0, -140, 0], opacity: [0.2, 0.9, 0.2], x: [0, -20 + Math.random() * 40, 0] }}
            transition={{ duration, repeat: Infinity, delay, ease: "easeInOut" }}
          />
        );
      })}
    </div>
  );
}
