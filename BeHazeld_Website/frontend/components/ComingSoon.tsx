import Link from "next/link";

type ComingSoonProps = {
  title: string;
  caption?: string;
};

export function ComingSoon({
  title,
  caption = "We will be with you soon with this section.",
}: ComingSoonProps) {
  return (
    <main className="relative z-10 min-h-[calc(100vh-64px)] overflow-hidden lg:min-h-[calc(100vh-80px)]">
      <section className="mx-auto flex min-h-[calc(100vh-64px)] max-w-7xl items-center justify-center px-6 py-16 lg:min-h-[calc(100vh-80px)]">
        <div className="relative grid w-full grid-cols-[minmax(112px,0.36fr)_1fr] items-center gap-6 border border-[rgba(192,147,48,0.24)] bg-[rgba(18,10,5,0.58)] px-5 py-12 text-left shadow-[0_28px_90px_rgba(0,0,0,0.36)] backdrop-blur-xl sm:grid-cols-[minmax(180px,0.42fr)_1fr] sm:gap-12 sm:px-10 sm:py-16 md:gap-16 md:px-14 lg:grid-cols-[360px_1fr] lg:gap-24 lg:px-20 lg:py-20">
          <div className="flex justify-end">
            <img
              src="/Logo.png"
              alt="BeHazel'd"
              className="h-24 w-auto sm:h-36 lg:h-44"
              style={{
                filter:
                  "brightness(1.85) contrast(1.12) saturate(1.35) drop-shadow(0 0 22px rgba(192,147,48,0.42))",
              }}
            />
          </div>

          <div>
            <p className="mb-4 text-[9px] uppercase tracking-[0.38em] text-[#C09330] sm:mb-5 sm:text-[10px] sm:tracking-[0.52em]">
              {title}
            </p>
            <h1 className="font-display text-4xl italic leading-none text-[#F8F0E8] sm:text-7xl lg:text-8xl">
              Coming Soon
            </h1>
            <p className="mt-6 max-w-2xl font-serif text-xl italic leading-snug text-[rgba(248,240,232,0.76)] sm:mt-8 sm:text-4xl">
              {caption}
            </p>

            <Link
              href="/atelier"
              className="mt-8 inline-flex h-10 items-center justify-center border border-[#C09330] px-4 text-[8px] uppercase tracking-[0.26em] text-[#F8F0E8] transition duration-300 hover:bg-[#C09330] hover:text-[#120A05] sm:mt-10 sm:h-11 sm:px-7 sm:text-[10px] sm:tracking-[0.36em]"
            >
              Return to Atelier
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
