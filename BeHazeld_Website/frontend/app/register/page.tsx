import type { Metadata } from "next";
import { RegistrationForm } from "@/components/registration/RegistrationForm";

export const metadata: Metadata = {
  title: "Register | BeHazel'd",
  description: "Register with BeHazel'd for personalized Chikankari collection guidance.",
};

export default function RegisterPage() {
  return (
    <main className="relative z-10">
      <section className="mx-auto flex min-h-[calc(100vh-64px)] max-w-7xl items-center justify-center px-5 py-8 sm:px-8 lg:min-h-[calc(100vh-80px)] lg:px-12">
        <RegistrationForm />
      </section>
    </main>
  );
}
