import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Private Atelier | BeHazel'd",
  description: "Begin a private BeHazel'd atelier conversation for personal styling and Chikankari edits.",
};

const whatsAppHref =
  "https://wa.me/918626060038?text=Hi";
const emailHref =
  "https://mail.google.com/mail/?view=cm&fs=1&to=Behazeld%40gmail.com";

export default function ConnectPage() {
  return (
    <main className="relative z-10 min-h-[calc(100vh-64px)] lg:min-h-[calc(100vh-80px)]">
      <section className="mx-auto flex min-h-[calc(100vh-64px)] max-w-7xl items-center justify-center px-6 py-14 text-center lg:min-h-[calc(100vh-80px)]">
        <div className="w-full">
          <p className="mb-12 text-[13px] uppercase tracking-[0.7em] text-[#C09330]">
            BeHazel'd
          </p>
          <h1 className="font-display text-[82px] italic leading-none text-[#F8F0E8] sm:text-[120px] lg:text-[150px]">
            Private Atelier
          </h1>
          <p className="mx-auto mt-16 max-w-5xl font-serif text-[38px] italic leading-[1.35] text-[rgba(248,240,232,0.78)] sm:text-[52px]">
            A quiet place to begin your personal Chikankari edit.
          </p>

          <div
            className="mx-auto mt-24 flex max-w-5xl flex-col items-center text-center"
            style={{ rowGap: "72px" }}
          >
            <a
              href={emailHref}
              target="_blank"
              rel="noreferrer"
              className="block font-serif text-[42px] italic leading-[1.25] text-[#F8F0E8] transition duration-300 hover:text-[#C09330] sm:text-[58px]"
            >
              Behazeld@gmail.com
            </a>

            <a
              href="https://www.instagram.com/behazeld/"
              target="_blank"
              rel="noreferrer"
              className="block font-serif text-[42px] italic leading-[1.25] text-[#F8F0E8] transition duration-300 hover:text-[#C09330] sm:text-[58px]"
            >
              @behazel'd
            </a>

            <a
              href={whatsAppHref}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-16 items-center justify-center bg-[#C09330] px-14 text-[13px] uppercase tracking-[0.46em] text-[#120A05] transition duration-300 hover:bg-[#F1D07A]"
            >
              Connect on WhatsApp
            </a>
          </div>

          <Link
            href="/atelier"
            className="mt-24 inline-flex text-[12px] uppercase tracking-[0.48em] text-[rgba(248,240,232,0.56)] transition hover:text-[#C09330]"
          >
            Return to Atelier
          </Link>
        </div>
      </section>
    </main>
  );
}
