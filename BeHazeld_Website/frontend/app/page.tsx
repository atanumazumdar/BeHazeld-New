import Image from "next/image";
import Link from "next/link";

export default function HomePage() {
  return (
    <main className="canva-home">
      <div className="canva-home__ornament" aria-hidden="true">
        <Image src="/Logo2.png" alt="" fill priority sizes="280px" className="object-contain" />
      </div>

      <section className="canva-home__composition" aria-labelledby="home-title">
        <div className="canva-home__film">
          <video
            src="/AnimatedLogoFinal.mp4"
            aria-label="BeHAZEL'd animated logo"
            autoPlay
            muted
            loop
            playsInline
            preload="metadata"
          />
        </div>

        <div className="canva-home__literature">
          <h1 id="home-title" className="canva-home__title">
            <span>Be you,</span>
            <span className="shimmer-gold">with HAZEL.</span>
          </h1>

          <p className="canva-home__belief">
            We believe fashion is not what you wear.....
            <br />
            it is what you become, when you wear it.
          </p>

          <div className="canva-home__thoughts" aria-label="Brand philosophy">
            <p>It stays with you.</p>
            <p>It evolves with you.</p>
            <p>It becomes you.</p>
          </div>

          <p className="canva-home__finale">You become it.</p>

          <Link href="/atelier" className="canva-home__cta">
            Explore the Atelier <span aria-hidden="true">→</span>
          </Link>
        </div>
      </section>

      <p className="canva-home__statement">
        Thoughtful silhouettes, rooted in Indian artistry and designed for women who move through every role with quiet confidence.
      </p>
    </main>
  );
}
