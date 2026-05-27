export default function WatermarkBg() {
  return (
    <>
      {/* Dual-tone mahogany gradient — fixed full-screen */}
      <div
        className="fixed inset-0 z-0 pointer-events-none"
        style={{
          background: 'linear-gradient(135deg, #120A05 0%, #2C1810 28%, #3D2314 55%, #2C1810 78%, #1A0E08 100%)',
        }}
      />

      {/* Logo2 — golden H — fixed centred watermark */}
      <div className="fixed inset-0 z-0 pointer-events-none flex items-center justify-center overflow-hidden">
        <img
          src="/Logo2.png"
          alt=""
          aria-hidden="true"
          draggable="false"
          className="select-none"
          style={{
            width: 'clamp(280px, 55vw, 680px)',
            opacity: 0.045,
            filter: 'sepia(1) saturate(3) hue-rotate(-5deg) brightness(1.2)',
          }}
        />
      </div>
    </>
  );
}
