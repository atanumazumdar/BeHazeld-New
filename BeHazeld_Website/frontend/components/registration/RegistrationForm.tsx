"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";

const FIELD =
  "h-[53px] w-full border-0 bg-[#9f8a6c] px-3 text-sm text-black outline-none transition placeholder:text-[rgba(0,0,0,0.45)] focus:bg-[#ad9878]";
const LABEL =
  "text-[15px] font-bold leading-none text-[rgba(248,240,232,0.88)]";

export function RegistrationForm() {
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <section className="glass-panel mx-auto max-w-xl px-6 py-16 text-center">
        <p className="text-[9px] font-normal uppercase tracking-[0.46em] text-[#C09330]">
          Registration received
        </p>
        <h1 className="font-serif mt-4 text-4xl font-light italic leading-tight text-[rgba(248,240,232,0.92)]">
          Welcome to the BeHAZEL&apos;d circle.
        </h1>
        <p className="mx-auto mt-5 max-w-md text-sm font-light leading-7 text-[rgba(177,152,112,0.82)]">
          Your details have been noted. Our atelier team will use this information to guide you toward the right Chikankari edit.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link href="/atelier" className="btn-couture inline-flex h-11 items-center justify-center px-7">
            The Atelier
          </Link>
          <button
            type="button"
            onClick={() => setSubmitted(false)}
            className="inline-flex h-11 items-center justify-center border border-[rgba(192,147,48,0.36)] px-7 text-[10px] font-light uppercase tracking-[0.28em] text-[#C09330] transition duration-300 hover:border-[#C09330] hover:bg-[rgba(192,147,48,0.12)] hover:text-[#F8F0E8]"
          >
            Register another
          </button>
        </div>
      </section>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-2xl">
      <section className="border-2 border-[rgba(192,147,48,0.34)] bg-transparent px-7 py-7 sm:px-8">
        <div className="mb-5 text-center">
          <p className="text-[9px] font-bold uppercase tracking-[0.46em] text-[rgba(248,240,232,0.88)]">
            Be Part of the Journey
          </p>
          <h1 className="font-serif mt-2 text-3xl font-bold italic leading-tight text-[rgba(248,240,232,0.92)] sm:text-4xl">
            Begin your BeHAZEL&apos;d journey.
          </h1>
          <p className="mx-auto mt-3 max-w-md text-sm font-bold leading-6 text-[rgba(248,240,232,0.78)]">
            Share your details and the collection mood that speaks to you. We&apos;ll use it to guide a more personal Chikankari edit.
          </p>
        </div>

        <div className="grid gap-2.5 text-left">
          <label className="space-y-2">
            <span className={LABEL}>Full name</span>
            <input required name="name" autoComplete="name" className={FIELD} />
          </label>
          <label className="space-y-2">
            <span className={LABEL}>Email</span>
            <input required name="email" type="email" autoComplete="email" className={FIELD} />
          </label>
          <label className="space-y-2">
            <span className={LABEL}>Phone (WhatsApp Number)</span>
            <input required name="phone" type="tel" autoComplete="tel" className={FIELD} />
          </label>
          <label className="space-y-2">
            <span className={LABEL}>Birth Day</span>
            <input required name="birthday" type="date" className={FIELD} />
          </label>
          <label className="space-y-2">
            <span className={LABEL}>Address</span>
            <input required name="address" autoComplete="street-address" className={FIELD} />
          </label>
          <label className="space-y-2">
            <span className={LABEL}>City</span>
            <input required name="city" autoComplete="address-level2" className={FIELD} />
          </label>
          <label className="space-y-2">
            <span className={LABEL}>Pin Code</span>
            <input required name="pin_code" autoComplete="postal-code" className={FIELD} />
          </label>
        </div>

        <label className="mt-3 block space-y-2 text-left">
          <span className={LABEL}>Style notes</span>
          <textarea
            name="notes"
            rows={5}
            className="w-full border-0 bg-[#9f8a6c] px-3 py-3 text-sm text-black outline-none transition placeholder:text-[rgba(0,0,0,0.45)] focus:bg-[#ad9878]"
            placeholder="Tell us what you are looking for: color, fit, occasion, timeline, or inspiration."
          />
        </label>

        <label className="mt-4 flex items-start gap-3 text-left text-sm font-bold leading-6 text-[rgba(248,240,232,0.78)]">
          <input required type="checkbox" className="mt-1 accent-[#C09330]" />
          I agree to be contacted by BeHAZEL&apos;d about collection guidance and atelier updates.
        </label>

        <div className="mt-6 flex justify-center">
          <button type="submit" className="btn-couture flex h-11 items-center justify-center px-8">
            Complete registration
          </button>
        </div>
      </section>
    </form>
  );
}
