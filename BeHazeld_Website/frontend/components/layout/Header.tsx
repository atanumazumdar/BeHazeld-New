import Link from "next/link";

import { CartLink } from "@/components/cart/CartLink";

const NAV_LINKS = [
  { label: "Our Story",      href: "/"              },
  { label: "The Atelier",    href: "/atelier"       },
  { label: "Ultra Luxe",     href: "/ultra-luxe"    },
  { label: "Accessories",    href: "/accessories"   },
  { label: "Pre Loved",      href: "/pre-loved"     },
  { label: "Private Atelier",href: "/connect"       },
  { label: "Register",       href: "/register"      },
];

export function Header() {
  return (
    <header
      className="sticky top-0 z-50 border-b"
      style={{
        background:          "rgba(18,10,5,0.84)",
        backdropFilter:      "blur(22px)",
        WebkitBackdropFilter:"blur(22px)",
        borderColor:         "rgba(192,147,48,0.16)",
      }}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:gap-6 sm:px-6 lg:h-20 lg:gap-10 lg:px-8 xl:gap-14">

        {/* Logo — links home */}
        <Link href="/" className="flex-shrink-0 leading-none" aria-label="BeHazel'd home">
          <img
            src="/Logo.png"
            alt="BeHAZEL'd"
            className="block w-auto"
            style={{
              height: "clamp(34px, 8vw, 46px)",
              filter: "brightness(1.85) contrast(1.12) saturate(1.35) drop-shadow(0 0 18px rgba(192,147,48,0.5))",
            }}
          />
        </Link>

        {/* Nav links */}
        <nav
          aria-label="Primary navigation"
          className="flex min-w-0 flex-1 items-center justify-start overflow-x-auto pb-1 sm:justify-end"
          style={{
            scrollbarWidth: "none",
            fontSize:       10,
            fontWeight:     300,
            columnGap:      "clamp(12px, 2vw, 42px)",
            letterSpacing:  "clamp(0.1em, 0.42vw, 0.18em)",
            textTransform:  "uppercase",
            color:          "rgba(248,240,232,0.62)",
          }}
        >
          {NAV_LINKS.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              className="inline-flex h-10 items-center whitespace-nowrap px-2 transition-colors duration-300 hover:text-[#C09330]"
            >
              {label}
            </Link>
          ))}

          <Link
            href="/checkout"
            className="hidden h-10 items-center whitespace-nowrap px-2 transition-colors duration-300 hover:text-[#C09330] xl:inline-flex"
          >
            Checkout
          </Link>

          <CartLink />

          {/*
           * Discreet admin link — intentionally low-contrast.
           * Only visible on xl screens (≥ 1280 px).
           * Anyone without the password cannot do anything useful from /admin/login.
           */}
          <Link
            href="/admin/login"
            aria-label="Admin"
            className="hidden xl:inline-flex h-10 items-center whitespace-nowrap px-2 transition-colors duration-300"
            style={{ color: "rgba(192,147,48,0.22)" }}
            onMouseOver={undefined}
            title="Admin"
          >
            ·
          </Link>
        </nav>
      </div>
    </header>
  );
}
