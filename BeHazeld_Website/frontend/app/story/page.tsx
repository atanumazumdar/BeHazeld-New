"use client";

import { useEffect, useRef, useState } from "react";
import { motion, type Variants } from "framer-motion";

/* ── Animation constants ─────────────────────────────────── */
const EASE_OUT  = [0.16, 1, 0.3, 1] as const;
const EASE_SILK = [0.76, 0, 0.24, 1] as const;

const PAGE: Variants = {
  initial: { opacity: 1 },
  animate: { opacity: 1, transition: { duration: 0.5, ease: "easeOut" } },
};

function up(delay: number) {
  return {
    initial: { opacity: 1, y: 0 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.75, ease: EASE_OUT, delay },
  };
}

function playVideo(video: HTMLVideoElement) {
  video.play().catch(() => {
    // Browsers may pause background media to save power; the user can restart it with controls.
  });
}

/* ── Shared styles ───────────────────────────────────────── */
const BODY: React.CSSProperties = {
  fontSize: 13.5, lineHeight: 1.82,
  color: "rgba(248,240,232,0.68)", letterSpacing: "0.027em",
};
const SERIF_ITALIC: React.CSSProperties = {
  fontFamily: "'Bodoni Moda', 'Cormorant Garamond', Georgia, serif",
  fontStyle: "italic", fontWeight: 300,
  color: "rgba(248,240,232,0.88)", lineHeight: 1.6,
};

/* ── Gold ornament ───────────────────────────────────────── */
function GoldRule({ delay }: { delay: number }) {
  return (
    <motion.div
      initial={{ scaleX: 1, opacity: 1 }}
      animate={{ scaleX: 1, opacity: 1 }}
      transition={{ duration: 0.8, ease: EASE_SILK, delay }}
      className="flex items-center gap-3 mb-4"
      style={{ transformOrigin: "left" }}
    >
      <div className="h-px w-10" style={{ background: "linear-gradient(to right, #C09330, rgba(192,147,48,0.12))" }} />
      <svg width="4" height="4" viewBox="0 0 6 6">
        <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill="#C09330" />
      </svg>
    </motion.div>
  );
}

export default function OurStoryPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const replayTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [isMuted, setIsMuted] = useState(true);

  useEffect(() => {
    const video = videoRef.current;

    if (!video) return;

    video.muted = isMuted;
    playVideo(video);
  }, [isMuted]);

  useEffect(() => {
    return () => {
      if (replayTimeoutRef.current) {
        clearTimeout(replayTimeoutRef.current);
      }
    };
  }, []);

  const toggleMusic = () => {
    const video = videoRef.current;

    if (!video) return;

    const nextMuted = !isMuted;
    video.muted = nextMuted;
    setIsMuted(nextMuted);

    if (!nextMuted) {
      playVideo(video);
    }
  };

  const handleVideoEnded = () => {
    const video = videoRef.current;

    if (!video) return;

    if (replayTimeoutRef.current) {
      clearTimeout(replayTimeoutRef.current);
    }

    replayTimeoutRef.current = setTimeout(() => {
      video.currentTime = 0;
      playVideo(video);
      replayTimeoutRef.current = null;
    }, 3000);
  };

  return (
    <motion.main
      variants={PAGE} initial="initial" animate="animate"
      className="story-layout relative z-10"
      style={{ minHeight: "calc(100vh - 64px)", paddingTop: 64, color: "#F8F0E8" }}
    >

      {/* ══════════════════════════════════════════════
          LEFT — sticky logo
      ════════════════════════════════════════════ */}
      <div
        className="story-logo-panel"
        style={{ top: 64, height: "calc(100vh - 64px)", alignSelf: "flex-start" }}
      >
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: "radial-gradient(ellipse 72% 60% at 50% 50%, rgba(192,147,48,0.11) 0%, transparent 68%)" }} />
        <div className="story-gold-thread absolute right-0 top-0 bottom-0 w-px pointer-events-none"
          style={{ background: "linear-gradient(to bottom, transparent 8%, rgba(192,147,48,0.23) 26%, rgba(192,147,48,0.23) 74%, transparent 92%)" }} />

        {/* Entrance → perpetual float */}
        <motion.div
          initial={{ opacity: 1, scale: 1.0, y: 0 }}
          animate={{ opacity: 1, scale: 1.0, y: 0 }}
          transition={{ duration: 1.5, ease: EASE_OUT }}
          className="relative z-10"
        >
          <motion.div
            animate={{ y: [0, -14, 0] }}
            transition={{ repeat: Infinity, duration: 6.0, ease: "easeInOut", delay: 1.9 }}
            className="relative"
          >
            <div className="absolute pointer-events-none"
              style={{ inset: "-24%", borderRadius: "50%", background: "radial-gradient(circle, rgba(192,147,48,0.20) 0%, transparent 65%)", filter: "blur(32px)" }} />
            <div
              className="relative mx-auto"
              style={{ width: "clamp(200px, 80%, 600px)" }}
            >
              <video
                ref={videoRef}
                src="/AnimatedLogoFinal.mp4"
                aria-label="BeHAZEL'd animated logo"
                autoPlay
                muted={isMuted}
                playsInline
                onEnded={handleVideoEnded}
                style={{
                  width: "100%", display: "block", margin: "0 auto",
                  filter: "brightness(1.12) contrast(0.82) saturate(0.96) sepia(0.12) drop-shadow(0 18px 44px rgba(192,147,48,0.18)) drop-shadow(0 4px 10px rgba(0,0,0,0.44))",
                }}
              />
              <div
                className="pointer-events-none absolute inset-0"
                style={{
                  background: "rgba(226, 204, 156, 0.16)",
                  mixBlendMode: "multiply",
                }}
              />
            </div>
          </motion.div>
        </motion.div>

        <motion.button
          {...up(1.55)}
          type="button"
          onClick={toggleMusic}
          className="relative z-10 mt-5 border border-[rgba(192,147,48,0.38)] px-5 py-2 font-sans text-[9px] font-light uppercase text-[#C09330] transition duration-300 hover:border-[#C09330] hover:bg-[rgba(192,147,48,0.12)] hover:text-[#F8F0E8]"
          style={{ letterSpacing: "0.34em" }}
        >
          {isMuted ? "Play Music" : "Mute Music"}
        </motion.button>

        <motion.p {...up(1.7)}
          className="story-tagline font-sans font-light uppercase mt-4"
          style={{ fontSize: 7.5, letterSpacing: "0.48em", color: "rgba(192,147,48,0.32)" }}>
          Handcrafted in India · Est. 2024
        </motion.p>
      </div>

      {/* ══════════════════════════════════════════════
          RIGHT — literature
      ════════════════════════════════════════════ */}
      <div
        className="story-content-panel"
        style={{ minHeight: "calc(100vh - 64px)" }}
      >
        <div className="relative w-full max-w-[600px]">

          <motion.p {...up(0.55)}
            className="font-sans font-normal uppercase mb-3"
            style={{ fontSize: 7.5, letterSpacing: "0.55em", color: "#C09330" }}>
            Est. 2024 · The Hazel Atelier
          </motion.p>

          {/* H1 — three-tier typographic cascade */}
          <div style={{ overflow: "hidden" }}>
            <motion.h1
              initial={{ y: 0 }} animate={{ y: 0 }}
              transition={{ duration: 1.1, ease: EASE_SILK, delay: 0.7 }}
              className="leading-none mb-4"
            >
              <span className="font-display font-light italic block"
                style={{ fontSize: "clamp(22px, 2.4vw, 34px)", color: "rgba(248,240,232,0.55)", lineHeight: 1.1 }}>
                The
              </span>
              <span className="shimmer-gold font-display italic block"
                style={{ fontSize: "clamp(42px, 4.8vw, 68px)", fontWeight: 700, lineHeight: 0.93 }}>
                Hazel
              </span>
              <span className="shimmer-gold font-display italic block"
                style={{ fontSize: "clamp(50px, 5.8vw, 84px)", fontWeight: 700, lineHeight: 0.9 }}>
                Story
              </span>
            </motion.h1>
          </div>

          <GoldRule delay={0.95} />

          {/* Opening quote */}
          <motion.p {...up(1.1)} className="font-display font-light italic mb-3"
            style={{ fontSize: "clamp(16px, 1.55vw, 19px)", ...SERIF_ITALIC }}>
            We believe fashion is not what you wear —
            it is what you become when you wear it.
          </motion.p>

          {/* Brand statement */}
          <motion.p {...up(1.2)} className="font-sans font-light mb-3"
            style={{ ...BODY, color: "rgba(248,240,232,0.80)" }}>
            <span style={{ color: "#C09330", fontWeight: 400 }}>BeHAZEL&apos;d</span>{" "}is not just a label. It is a story — Hazel&apos;s story.
          </motion.p>

          {/* Body §1 */}
          <motion.p {...up(1.3)} className="font-sans font-light mb-3" style={BODY}>
            Born in Mumbai and shaped by boardrooms across continents, Hazel built a career with a Fortune 500
            organisation across geographies and time zones — each country a new layer, each culture a new
            perspective. Yet somewhere between airports and deadlines, she began searching for something
            quieter. Something more rooted.
          </motion.p>

          {/* Pull line */}
          <motion.p {...up(1.4)} className="font-display font-light italic mb-3"
            style={{ fontSize: "clamp(15px, 1.45vw, 18px)", ...SERIF_ITALIC, color: "rgba(248,240,232,0.82)" }}>
            She found it in the timeless artistry of Lucknow.
          </motion.p>

          {/* Body §2 */}
          <motion.p {...up(1.5)} className="font-sans font-light mb-3" style={BODY}>
            In the meditative craft of Chikan embroidery she discovered a rhythm mirroring her own journey —
            patient, intricate, expressive. BeHAZEL&apos;d was born from that moment of return: every piece global
            in exposure, deeply Indian in soul, designed for women who move across roles and moments with
            quiet strength.
          </motion.p>

          {/* Gold border accent block */}
          <motion.div {...up(1.6)} className="pl-4 mb-3"
            style={{ borderLeft: "2px solid rgba(192,147,48,0.45)" }}>
            <p className="font-sans font-light"
              style={{ ...BODY, lineHeight: 1.9, color: "rgba(248,240,232,0.76)" }}>
              For all moods. For all occasions.
            </p>
            <p className="font-sans font-light"
              style={{ ...BODY, lineHeight: 1.9, color: "rgba(248,240,232,0.76)" }}>
              For all ages, all classes — because elegance does not discriminate.
            </p>
          </motion.div>

          {/* Poetry */}
          <motion.div {...up(1.7)} className="mb-3">
            <p className="font-display font-light italic"
              style={{ fontSize: "clamp(14px, 1.35vw, 16.5px)", ...SERIF_ITALIC, lineHeight: 1.78, color: "rgba(248,240,232,0.80)" }}>
              It stays with you. It evolves with you. It becomes you.
            </p>
          </motion.div>

          {/* Finale */}
          <motion.p {...up(1.8)} className="font-display font-light italic mb-5"
            style={{ fontSize: "clamp(20px, 2.05vw, 27px)", color: "#C09330", lineHeight: 1.2 }}>
            You become it.
          </motion.p>

          <motion.p {...up(2.05)}
            className="font-display ml-auto mt-8 text-right font-light italic"
            style={{ fontSize: "clamp(17px, 1.45vw, 21px)", fontFamily: "'Bodoni Moda', 'Cormorant Garamond', Georgia, serif", color: "rgba(192,147,48,0.65)" }}>
            be you, with HAZEL
          </motion.p>

        </div>
      </div>
    </motion.main>
  );
}
